"""Sentence-transformers wrapper for local CPU embedding.

Defaults to `BAAI/bge-small-en-v1.5` — MIT-licensed, 384-dim, retrieval-trained,
~133 MB first-run download to the Hugging Face cache.
"""

from __future__ import annotations

from .config import EMBED_MODEL


class Embedder:
    """Thin wrapper that encodes texts to L2-normalized float vectors."""

    def __init__(self, model_name: str = EMBED_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device="cpu")
        # `get_embedding_dimension` is the post-3.x name; some older versions
        # only ship `get_sentence_embedding_dimension`. Branch on hasattr so
        # whichever method is missing is never referenced.
        if hasattr(self._model, "get_embedding_dimension"):
            self._dim = int(self._model.get_embedding_dimension())
        else:
            self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # No client-side normalization: Qdrant's Distance.COSINE normalizes
        # vectors server-side, so pre-normalizing here would be redundant
        # work without changing retrieval scores.
        vectors = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vectors.tolist()
