"""Runtime configuration: env vars and constants. No I/O, no SDK calls."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Repository root so relative defaults resolve regardless of CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME: str = os.environ.get("RAG_COLLECTION", "markdown-rag")
EMBED_MODEL: str = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
ANTHROPIC_MODEL: str = os.environ.get("RAG_ANTHROPIC_MODEL", "claude-sonnet-4-6")
TOP_K: int = int(os.environ.get("RAG_TOP_K", "5"))
BATCH_SIZE: int = int(os.environ.get("RAG_BATCH_SIZE", "32"))
MAX_TOKENS: int = int(os.environ.get("RAG_MAX_TOKENS", "1024"))
# CORPUS_DIR resolves relative to the repo root by default so `python rag.py
# ingest` works from any CWD. Override with an absolute path or any path
# resolvable from the user's working directory.
CORPUS_DIR: str = os.environ.get("RAG_CORPUS_DIR", str(_REPO_ROOT / "corpus"))

# Namespace for deterministic UUIDv5 chunk IDs. Default is fixed so re-ingest
# overwrites in place; users running multiple independent collections can
# override to keep their chunk IDs distinct.
_DEFAULT_NAMESPACE = "6d4e9a3a-3b1f-4f1b-8b9a-6c1d2c5e7f10"


def _parse_namespace(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        die(f"RAG_NAMESPACE must be a valid UUID, got: {value!r}")
        raise  # unreachable — die() exits, but keep the type-checker happy


def die(message: str, code: int = 1) -> None:
    """Print a one-line friendly error to stderr and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


RAG_NAMESPACE: uuid.UUID = _parse_namespace(os.environ.get("RAG_NAMESPACE", _DEFAULT_NAMESPACE))


def require_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        die(
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key, or export it in your shell."
        )
    return key  # type: ignore[return-value]
