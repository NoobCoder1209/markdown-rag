"""Thin entrypoint so `python rag.py ...` works from a fresh clone."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rag.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
