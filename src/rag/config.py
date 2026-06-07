"""Runtime configuration: env vars and constants. No I/O, no SDK calls."""

from __future__ import annotations

import os
import sys

QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME: str = os.environ.get("RAG_COLLECTION", "markdown-rag")
EMBED_MODEL: str = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
ANTHROPIC_MODEL: str = os.environ.get("RAG_ANTHROPIC_MODEL", "claude-sonnet-4-6")
TOP_K: int = int(os.environ.get("RAG_TOP_K", "5"))
BATCH_SIZE: int = int(os.environ.get("RAG_BATCH_SIZE", "32"))
MAX_TOKENS: int = int(os.environ.get("RAG_MAX_TOKENS", "1024"))
CORPUS_DIR: str = os.environ.get("RAG_CORPUS_DIR", "corpus")


def die(message: str, code: int = 1) -> None:
    """Print a one-line friendly error to stderr and exit non-zero."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def require_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        die(
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key, or export it in your shell."
        )
    return key  # type: ignore[return-value]
