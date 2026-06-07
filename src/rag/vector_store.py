"""Qdrant client wrapper. Idempotent ensure-collection and payload-index,
batched upsert, query_points-based search, and an exponential-backoff
readiness probe so `make demo` survives Docker startup latency.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException, UnexpectedResponse
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from .config import COLLECTION_NAME, QDRANT_URL


@dataclass
class ScoredChunk:
    """A retrieval hit decoded back into a chunk-like object."""

    score: float
    text: str
    source_file: str
    heading_path: list[str]


class VectorStore:
    def __init__(self, url: str = QDRANT_URL, collection: str = COLLECTION_NAME) -> None:
        self.url = url
        self.collection = collection
        self._client = QdrantClient(url=url, timeout=10.0)

    @property
    def client(self) -> QdrantClient:
        return self._client

    def wait_until_ready(self, *, max_attempts: int = 8, base_delay: float = 0.5) -> None:
        """Block until Qdrant answers, retrying with exponential backoff."""
        delay = base_delay
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                self._client.get_collections()
                return
            except (httpx.HTTPError, ApiException, UnexpectedResponse) as exc:
                last_exc = exc
                if attempt == max_attempts:
                    break
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(
            f"Qdrant unreachable at {self.url} after {max_attempts} attempts"
        ) from last_exc

    def ensure_collection(self, dim: int) -> None:
        if self._client.collection_exists(self.collection):
            return
        self._client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    def ensure_payload_index(self, field_name: str = "source_file") -> None:
        # Idempotent: re-creating an identical payload index is a no-op server-side.
        with contextlib.suppress(UnexpectedResponse):
            self._client.create_payload_index(
                collection_name=self.collection,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def upsert(self, points: Iterable[dict[str, Any]], batch_size: int = 32) -> int:
        """Upsert dicts shaped {id, vector, text, source_file, heading_path}."""
        buf: list[PointStruct] = []
        total = 0
        for row in points:
            buf.append(
                PointStruct(
                    id=row["id"],
                    vector=row["vector"],
                    payload={
                        "text": row["text"],
                        "source_file": row["source_file"],
                        "heading_path": row["heading_path"],
                    },
                )
            )
            if len(buf) >= batch_size:
                self._client.upsert(collection_name=self.collection, points=buf, wait=True)
                total += len(buf)
                buf.clear()
        if buf:
            self._client.upsert(collection_name=self.collection, points=buf, wait=True)
            total += len(buf)
        return total

    def query(self, vector: list[float], top_k: int = 5) -> list[ScoredChunk]:
        resp = self._client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        out: list[ScoredChunk] = []
        for hit in resp.points:
            payload = hit.payload or {}
            out.append(
                ScoredChunk(
                    score=float(hit.score),
                    text=str(payload.get("text", "")),
                    source_file=str(payload.get("source_file", "")),
                    heading_path=list(payload.get("heading_path") or []),
                )
            )
        return out

    def reset(self) -> None:
        if self._client.collection_exists(self.collection):
            self._client.delete_collection(collection_name=self.collection)

    def count(self) -> int:
        if not self._client.collection_exists(self.collection):
            return 0
        return int(self._client.count(self.collection, exact=True).count)
