"""Ingest a corpus directory into Qdrant: walk → chunk → embed → upsert."""

from __future__ import annotations

import uuid
from pathlib import Path

from .chunking import Chunk, chunk_file
from .config import BATCH_SIZE, CORPUS_DIR
from .embeddings import Embedder
from .vector_store import VectorStore

# Fixed namespace UUID so chunk IDs are deterministic across runs.
# Generated once with uuid.uuid4(); do NOT change — it would orphan existing points.
RAG_NAMESPACE = uuid.UUID("6d4e9a3a-3b1f-4f1b-8b9a-6c1d2c5e7f10")


def _chunk_id(chunk: Chunk, index: int) -> str:
    name = f"{chunk.source_file}::{'/'.join(chunk.heading_path)}::{index}"
    return str(uuid.uuid5(RAG_NAMESPACE, name))


def _walk_corpus(root: Path) -> list[Chunk]:
    if not root.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {root}")
    chunks: list[Chunk] = []
    for path in sorted(root.rglob("*.md")):
        chunks.extend(chunk_file(path))
    return chunks


def ingest(corpus_dir: str | Path = CORPUS_DIR) -> dict[str, int]:
    root = Path(corpus_dir)
    chunks = _walk_corpus(root)
    if not chunks:
        return {"files": 0, "chunks": 0, "upserted": 0}

    embedder = Embedder()
    store = VectorStore()
    store.wait_until_ready()
    store.ensure_collection(dim=embedder.dim)
    store.ensure_payload_index("source_file")

    rows: list[dict] = []
    per_file_index: dict[str, int] = {}
    texts = [c.text for c in chunks]
    vectors = _encode_in_batches(embedder, texts, BATCH_SIZE)

    for chunk, vector in zip(chunks, vectors, strict=True):
        idx = per_file_index.get(chunk.source_file, 0)
        per_file_index[chunk.source_file] = idx + 1
        rows.append(
            {
                "id": _chunk_id(chunk, idx),
                "vector": vector,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "heading_path": chunk.heading_path,
            }
        )

    upserted = store.upsert(rows, batch_size=BATCH_SIZE)
    files = len({c.source_file for c in chunks})
    return {"files": files, "chunks": len(chunks), "upserted": upserted}


def _encode_in_batches(embedder: Embedder, texts: list[str], batch_size: int) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        out.extend(embedder.encode(texts[i : i + batch_size]))
    return out
