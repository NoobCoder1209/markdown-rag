"""Embed the user query and fetch the top-k nearest chunks from Qdrant."""

from __future__ import annotations

from .config import TOP_K
from .embeddings import Embedder
from .vector_store import ScoredChunk, VectorStore


def retrieve(query: str, top_k: int = TOP_K) -> list[ScoredChunk]:
    embedder = Embedder()
    store = VectorStore()
    store.wait_until_ready()
    [vector] = embedder.encode([query])
    return store.query(vector, top_k=top_k)
