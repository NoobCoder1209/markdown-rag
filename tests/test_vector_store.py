"""Unit tests for VectorStore. All Qdrant interactions are mocked."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from qdrant_client.http.exceptions import UnexpectedResponse

from rag.vector_store import ScoredChunk, VectorStore


def _make_store() -> tuple[VectorStore, MagicMock]:
    """Build a VectorStore with a fully-mocked QdrantClient injected."""
    with patch("rag.vector_store.QdrantClient") as qdrant_cls:
        fake_client = MagicMock()
        qdrant_cls.return_value = fake_client
        store = VectorStore(url="http://fake:6333", collection="test-col")
    return store, fake_client


def test_wait_until_ready_retries_then_succeeds() -> None:
    store, fake = _make_store()
    # Fail twice, then succeed.
    fake.get_collections.side_effect = [
        httpx.ConnectError("boom"),
        httpx.ConnectError("boom"),
        SimpleNamespace(collections=[]),
    ]
    with patch("rag.vector_store.time.sleep") as sleep_mock:
        store.wait_until_ready(max_attempts=5, base_delay=0.01)
    assert fake.get_collections.call_count == 3
    # Slept twice between the three attempts.
    assert sleep_mock.call_count == 2


def test_wait_until_ready_raises_after_max_attempts() -> None:
    store, fake = _make_store()
    fake.get_collections.side_effect = httpx.ConnectError("nope")
    with patch("rag.vector_store.time.sleep"), pytest.raises(RuntimeError, match="unreachable"):
        store.wait_until_ready(max_attempts=3, base_delay=0.0)
    assert fake.get_collections.call_count == 3


def test_ensure_collection_is_idempotent() -> None:
    store, fake = _make_store()
    # First call: collection does not exist; second call: it does.
    fake.collection_exists.side_effect = [False, True]
    store.ensure_collection(dim=4)
    store.ensure_collection(dim=4)
    # create_collection only called the first time.
    assert fake.create_collection.call_count == 1


def test_ensure_payload_index_swallows_unexpected_response() -> None:
    store, fake = _make_store()
    fake.create_payload_index.side_effect = UnexpectedResponse(
        status_code=400, reason_phrase="bad", content=b"already exists", headers=None
    )
    # Must NOT raise.
    store.ensure_payload_index("source_file")
    assert fake.create_payload_index.call_count == 1


def test_query_maps_query_points_response_into_scored_chunks() -> None:
    store, fake = _make_store()
    hit1 = SimpleNamespace(
        score=0.91,
        payload={
            "text": "alpha body",
            "source_file": "a.md",
            "heading_path": ["Top", "A"],
        },
    )
    hit2 = SimpleNamespace(
        score=0.72,
        payload={"text": "beta body", "source_file": "b.md", "heading_path": None},
    )
    fake.query_points.return_value = SimpleNamespace(points=[hit1, hit2])

    out = store.query([0.1, 0.2, 0.3], top_k=2)
    assert len(out) == 2
    assert out[0] == ScoredChunk(
        score=0.91, text="alpha body", source_file="a.md", heading_path=["Top", "A"]
    )
    # heading_path None should be coerced to [].
    assert out[1].heading_path == []
    fake.query_points.assert_called_once()
    kwargs = fake.query_points.call_args.kwargs
    assert kwargs["limit"] == 2
    assert kwargs["with_payload"] is True


def test_upsert_batches_correctly() -> None:
    store, fake = _make_store()

    # The implementation clears its internal buf in-place between calls, so a
    # plain MagicMock would observe the same list reference. Capture sizes
    # eagerly via a side_effect.
    sizes: list[int] = []

    def capture(**kwargs):  # noqa: ANN001, ANN202
        sizes.append(len(kwargs["points"]))

    fake.upsert.side_effect = capture
    rows = [
        {
            "id": str(i),
            "vector": [0.0, 0.0],
            "text": f"t{i}",
            "source_file": "x.md",
            "heading_path": [],
        }
        for i in range(33)
    ]
    total = store.upsert(rows, batch_size=32)
    assert total == 33
    # 33 items at batch_size=32 → exactly 2 upsert calls (32 + 1).
    assert fake.upsert.call_count == 2
    assert sizes == [32, 1]


def test_upsert_empty_iterable_makes_no_calls() -> None:
    store, fake = _make_store()
    total = store.upsert([], batch_size=32)
    assert total == 0
    fake.upsert.assert_not_called()


def test_reset_is_safe_when_collection_missing() -> None:
    store, fake = _make_store()
    fake.collection_exists.return_value = False
    store.reset()
    fake.delete_collection.assert_not_called()


def test_reset_deletes_when_collection_exists() -> None:
    store, fake = _make_store()
    fake.collection_exists.return_value = True
    store.reset()
    fake.delete_collection.assert_called_once_with(collection_name="test-col")
