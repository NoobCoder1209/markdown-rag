"""Unit tests for answer module helpers (no Anthropic SDK calls)."""

from __future__ import annotations

from rag.answer import _dedup_sources, _heading_label, build_user_message
from rag.vector_store import ScoredChunk


def _chunk(source: str, headings: list[str], text: str = "body") -> ScoredChunk:
    return ScoredChunk(score=0.5, text=text, source_file=source, heading_path=headings)


def test_heading_label_empty_path_returns_placeholder() -> None:
    assert _heading_label(_chunk("a.md", [])) == "(no heading)"


def test_heading_label_joins_with_separator() -> None:
    assert _heading_label(_chunk("a.md", ["Top", "A", "Sub"])) == "Top > A > Sub"


def test_build_user_message_with_empty_chunk_list() -> None:
    msg = build_user_message([], "what is k8s?")
    assert "(no context retrieved)" in msg
    assert msg.startswith("<context>")
    assert msg.rstrip().endswith("Question: what is k8s?")


def test_build_user_message_uses_no_heading_placeholder_for_empty_path() -> None:
    chunks = [_chunk("plain.md", [], text="raw body")]
    msg = build_user_message(chunks, "q?")
    assert "[plain.md > (no heading)]" in msg
    assert "raw body" in msg


def test_dedup_sources_empty() -> None:
    assert _dedup_sources([]) == []


def test_dedup_sources_all_distinct() -> None:
    chunks = [
        _chunk("a.md", ["Top", "A"]),
        _chunk("b.md", ["Top", "B"]),
        _chunk("a.md", ["Top", "C"]),  # same file, different last heading
    ]
    out = _dedup_sources(chunks)
    assert out == [
        "- a.md > A",
        "- b.md > B",
        "- a.md > C",
    ]


def test_dedup_sources_all_duplicate_collapses_to_one() -> None:
    same = _chunk("a.md", ["Top", "Section"])
    out = _dedup_sources([same, same, same])
    assert out == ["- a.md > Section"]


def test_dedup_sources_handles_empty_heading_path() -> None:
    chunks = [
        _chunk("a.md", []),
        _chunk("a.md", []),  # duplicate of the above
        _chunk("b.md", []),
    ]
    out = _dedup_sources(chunks)
    assert out == [
        "- a.md > (no heading)",
        "- b.md > (no heading)",
    ]


def test_dedup_sources_preserves_first_occurrence_order() -> None:
    chunks = [
        _chunk("z.md", ["Z"]),
        _chunk("a.md", ["A"]),
        _chunk("z.md", ["Z"]),  # dupe of first
    ]
    out = _dedup_sources(chunks)
    # z.md must appear before a.md, exactly once.
    assert out == ["- z.md > Z", "- a.md > A"]
