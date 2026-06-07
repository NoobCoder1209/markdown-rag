"""Unit tests for ingest. Mocks Embedder and VectorStore so no real I/O happens."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag.chunking import Chunk
from rag.ingest import RAG_NAMESPACE, _chunk_id, _encode_in_batches, _walk_corpus, ingest


def test_chunk_id_is_deterministic_uuidv5() -> None:
    chunk = Chunk(text="body", source_file="x.md", heading_path=["Top", "A"])
    a = _chunk_id(chunk, 0)
    b = _chunk_id(chunk, 0)
    assert a == b
    # Verify it is a valid UUID v5 derived from the project namespace.
    expected = str(uuid.uuid5(RAG_NAMESPACE, "x.md::Top/A::0"))
    assert a == expected


def test_chunk_id_changes_with_index() -> None:
    chunk = Chunk(text="body", source_file="x.md", heading_path=["Top"])
    assert _chunk_id(chunk, 0) != _chunk_id(chunk, 1)


def test_chunk_id_distinguishes_source_file_and_heading_path() -> None:
    a = _chunk_id(Chunk(text="b", source_file="a.md", heading_path=["X"]), 0)
    b = _chunk_id(Chunk(text="b", source_file="b.md", heading_path=["X"]), 0)
    c = _chunk_id(Chunk(text="b", source_file="a.md", heading_path=["Y"]), 0)
    assert len({a, b, c}) == 3


def test_walk_corpus_raises_for_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError, match="corpus directory not found"):
        _walk_corpus(missing)


def test_walk_corpus_skips_non_md_files_and_returns_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("# B\n\nbeta body.\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\n\nalpha body.\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("not markdown\n", encoding="utf-8")
    (tmp_path / "notes.org").write_text("not markdown\n", encoding="utf-8")

    chunks = _walk_corpus(tmp_path)
    sources = [c.source_file for c in chunks]
    # Sorted alphabetically: a.md before b.md.
    assert sources.index("a.md") < sources.index("b.md")
    # No non-markdown files appear.
    assert all(s.endswith(".md") for s in sources)


def test_encode_in_batches_calls_embedder_correct_number_of_times() -> None:
    embedder = MagicMock()
    embedder.encode.side_effect = lambda texts: [[float(i)] for i, _ in enumerate(texts)]

    texts = [f"t{i}" for i in range(7)]
    out = _encode_in_batches(embedder, texts, batch_size=3)
    # ceil(7/3) = 3 calls.
    assert embedder.encode.call_count == 3
    assert len(out) == 7
    # Inspect batch sizes passed in.
    sizes = [len(call.args[0]) for call in embedder.encode.call_args_list]
    assert sizes == [3, 3, 1]


def test_encode_in_batches_empty_input() -> None:
    embedder = MagicMock()
    out = _encode_in_batches(embedder, [], batch_size=4)
    assert out == []
    embedder.encode.assert_not_called()


def test_ingest_end_to_end_produces_stable_ids(tmp_path: Path) -> None:
    """Run ingest twice on the same corpus; the chunk IDs upserted must match."""
    (tmp_path / "note.md").write_text(
        "# Top\n\n## A\n\nbody alpha.\n\n## B\n\nbody beta.\n",
        encoding="utf-8",
    )

    captured_ids: list[list[str]] = []

    def make_store_mock() -> MagicMock:
        store = MagicMock()

        def fake_upsert(rows, batch_size=32):  # noqa: ANN001, ANN202
            ids = [r["id"] for r in rows]
            captured_ids.append(ids)
            return len(ids)

        store.upsert.side_effect = fake_upsert
        return store

    fake_embedder = MagicMock()
    fake_embedder.dim = 4
    # Return a deterministic vector per text.
    fake_embedder.encode.side_effect = lambda texts: [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    with (
        patch("rag.ingest.Embedder", return_value=fake_embedder),
        patch("rag.ingest.VectorStore", side_effect=lambda: make_store_mock()),
    ):
        result1 = ingest(tmp_path)
        result2 = ingest(tmp_path)

    assert result1["chunks"] > 0
    assert result1 == result2
    assert captured_ids[0] == captured_ids[1]
    # Each ID is a valid UUID string.
    for cid in captured_ids[0]:
        uuid.UUID(cid)


def test_ingest_returns_zeroes_for_empty_corpus(tmp_path: Path) -> None:
    # No .md files in the directory.
    (tmp_path / "ignore.txt").write_text("nope\n", encoding="utf-8")
    # Embedder/VectorStore should not even be constructed in this branch, but
    # patch them defensively to keep the test hermetic.
    with (
        patch("rag.ingest.Embedder") as embedder_cls,
        patch("rag.ingest.VectorStore") as store_cls,
    ):
        result = ingest(tmp_path)
    assert result == {"files": 0, "chunks": 0, "upserted": 0}
    embedder_cls.assert_not_called()
    store_cls.assert_not_called()


def test_ingest_deletes_each_source_file_before_upsert(tmp_path: Path) -> None:
    """For every file in the corpus, ingest must call delete_by_source_file
    before the upsert for that file. This guarantees that section-level edits
    (insertions, removals) never leave orphan vectors behind.
    """
    (tmp_path / "alpha.md").write_text("# A\n\nalpha body.\n", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# B\n\nbeta body.\n", encoding="utf-8")

    fake_embedder = MagicMock()
    fake_embedder.dim = 4
    fake_embedder.encode.side_effect = lambda texts: [[0.0, 0.0, 0.0, 0.0] for _ in texts]

    fake_store = MagicMock()
    fake_store.upsert.side_effect = lambda rows, batch_size=32: len(rows)

    # Record the order of delete/upsert calls so we can assert delete-then-upsert.
    call_log: list[tuple[str, str]] = []
    fake_store.delete_by_source_file.side_effect = lambda sf: call_log.append(("delete", sf))
    original_upsert = fake_store.upsert.side_effect

    def upsert_with_log(rows, batch_size=32):  # noqa: ANN001, ANN202
        sources = {r["source_file"] for r in rows}
        for s in sources:
            call_log.append(("upsert", s))
        return original_upsert(rows, batch_size)

    fake_store.upsert.side_effect = upsert_with_log

    with (
        patch("rag.ingest.Embedder", return_value=fake_embedder),
        patch("rag.ingest.VectorStore", return_value=fake_store),
    ):
        result = ingest(tmp_path)

    assert result["files"] == 2
    # Every file must see (delete, file) before (upsert, file).
    for sf in ("alpha.md", "beta.md"):
        delete_idx = call_log.index(("delete", sf))
        upsert_idx = call_log.index(("upsert", sf))
        assert delete_idx < upsert_idx, f"upsert before delete for {sf}: {call_log}"
