"""End-to-end smoke test that mocks Qdrant + Anthropic + sentence-transformers.

Verifies the CLI wiring: `ask` retrieves chunks, builds a prompt, streams an
answer, and prints the Sources footer with the correct deduplication.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from rag.cli import app
from rag.vector_store import ScoredChunk

runner = CliRunner()


def _fake_chunks() -> list[ScoredChunk]:
    return [
        ScoredChunk(
            score=0.91,
            text="Default-deny is the first NetworkPolicy you should write.",
            source_file="10-network-policies.md",
            heading_path=["Network Policies", "A default-deny baseline"],
        ),
        ScoredChunk(
            score=0.84,
            text="A Service has a selector that matches Pod labels.",
            source_file="06-services-and-endpoints.md",
            heading_path=["Services and Endpoints", "How selectors map to endpoints"],
        ),
        # Same source_file + last heading as the first chunk — should be deduped.
        ScoredChunk(
            score=0.80,
            text="Egress policies are easy to misconfigure.",
            source_file="10-network-policies.md",
            heading_path=["Network Policies", "A default-deny baseline"],
        ),
    ]


class _FakeStream:
    """Stand-in for `client.messages.stream(...)` context manager."""

    def __init__(self, parts: list[str]) -> None:
        self._parts = parts

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    @property
    def text_stream(self):  # noqa: ANN201
        yield from self._parts


def test_ask_streams_answer_and_prints_sources() -> None:
    fake_client = MagicMock()
    fake_client.messages.stream.return_value = _FakeStream(
        ["Use a ", "default-deny ", "NetworkPolicy."]
    )

    with (
        patch("rag.retrieve.retrieve", return_value=_fake_chunks()),
        patch("rag.answer.require_api_key", return_value="test-key"),
        patch("anthropic.Anthropic", return_value=fake_client),
    ):
        result = runner.invoke(app, ["ask", "How do I lock down a namespace?"])

    assert result.exit_code == 0, result.output
    assert "default-deny" in result.output
    assert "Sources:" in result.output
    assert "10-network-policies.md > A default-deny baseline" in result.output
    assert "06-services-and-endpoints.md > How selectors map to endpoints" in result.output
    # Duplicate (same file + same last heading) should appear exactly once.
    assert result.output.count("10-network-policies.md > A default-deny baseline") == 1


def test_ask_with_empty_corpus_errors_friendly() -> None:
    with patch("rag.retrieve.retrieve", return_value=[]):
        result = runner.invoke(app, ["ask", "anything"])
    assert result.exit_code != 0
    assert "ingest" in result.output.lower()


def test_build_user_message_format() -> None:
    from rag.answer import build_user_message

    msg = build_user_message(_fake_chunks(), "How do I lock down a namespace?")
    assert msg.startswith("<context>")
    assert msg.rstrip().endswith("Question: How do I lock down a namespace?")
    assert "[10-network-policies.md > Network Policies > A default-deny baseline]" in msg
    assert "---" in msg
