"""Embedding service with batching, caching, and token tracking.

Supports OpenAI embeddings with automatic batching for large document sets.
Tracks token usage for cost monitoring via Prometheus metrics.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import get_settings
from src.core.exceptions import EmbeddingError
from src.core.logging import get_logger
from src.monitoring.metrics import EMBEDDING_TOKENS, EMBEDDING_LATENCY

logger = get_logger(__name__)

# Maximum batch size for OpenAI embedding API
MAX_BATCH_SIZE = 2048


class EmbeddingService:
    """Generates and caches text embeddings using OpenAI's API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.openai_embedding_model
        self._dimensions = settings.embedding_dimensions
        self._cache: dict[str, list[float]] = {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            EmbeddingError: If the OpenAI API call fails after retries.
        """
        if not texts:
            return []

        # Check cache first
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []
        results: dict[int, list[float]] = {}

        for i, text in enumerate(texts):
            cache_key = self._cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            embeddings = await self._batch_embed(uncached_texts)
            for idx, embedding in zip(uncached_indices, embeddings):
                cache_key = self._cache_key(texts[idx])
                self._cache[cache_key] = embedding
                results[idx] = embedding

        return [results[i] for i in range(len(texts))]

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query string."""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    async def _batch_embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches to respect API limits."""
        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[batch_start : batch_start + MAX_BATCH_SIZE]

            try:
                with EMBEDDING_LATENCY.time():
                    response = await self._client.embeddings.create(
                        model=self._model,
                        input=batch,
                    )

                batch_embeddings = [
                    item.embedding for item in sorted(response.data, key=lambda x: x.index)
                ]
                all_embeddings.extend(batch_embeddings)

                # Track token usage
                if response.usage:
                    EMBEDDING_TOKENS.inc(response.usage.total_tokens)

                logger.debug(
                    "batch_embedded",
                    batch_size=len(batch),
                    tokens=response.usage.total_tokens if response.usage else 0,
                )

            except Exception as e:
                raise EmbeddingError(
                    f"Embedding API call failed: {e}"
                ) from e

        return all_embeddings

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def clear_cache(self) -> None:
        self._cache.clear()
