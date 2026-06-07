"""Ingest a corpus directory into Qdrant: walk → chunk → embed → upsert.

Per-file delete-then-upsert keeps the collection in sync with on-disk
content. If a section is added or removed mid-file, all old points for
that file are evicted before the fresh chunks land — no orphans.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from pathlib import Path

from .chunking import Chunk, chunk_file
from .config import BATCH_SIZE, CORPUS_DIR, RAG_NAMESPACE
from .embeddings import Embedder
from .vector_store import VectorStore


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


def _group_by_file(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.source_file].append(chunk)
    return grouped


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

    grouped = _group_by_file(chunks)
    total_upserted = 0

    for source_file, file_chunks in grouped.items():
        # Evict any prior points for this file so re-ingest after edits
        # never leaves orphans. Cheap thanks to the keyword payload index.
        store.delete_by_source_file(source_file)

        texts = [c.text for c in file_chunks]
        vectors = _encode_in_batches(embedder, texts, BATCH_SIZE)
        rows = [
            {
                "id": _chunk_id(chunk, idx),
                "vector": vector,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "heading_path": chunk.heading_path,
            }
            for idx, (chunk, vector) in enumerate(zip(file_chunks, vectors, strict=True))
        ]
        total_upserted += store.upsert(rows, batch_size=BATCH_SIZE)

    return {"files": len(grouped), "chunks": len(chunks), "upserted": total_upserted}


def _encode_in_batches(embedder: Embedder, texts: list[str], batch_size: int) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        out.extend(embedder.encode(texts[i : i + batch_size]))
    return out
