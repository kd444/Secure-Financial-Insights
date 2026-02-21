"""Vector store abstraction with support for ChromaDB and Pinecone.

Provides hybrid search combining dense (semantic) and sparse (keyword) retrieval,
with metadata filtering for company-specific and filing-type queries.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.core.config import VectorStoreProvider, get_settings
from src.core.exceptions import RetrievalError
from src.core.logging import get_logger
from src.models.schemas import DocumentChunk

logger = get_logger(__name__)


class VectorStoreBase(ABC):
    """Abstract base for vector store implementations."""

    @abstractmethod
    async def add_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        """Store document chunks with their embeddings."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks by embedding vector."""

    @abstractmethod
    async def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks belonging to a document."""

    @abstractmethod
    async def get_collection_stats(self) -> dict[str, Any]:
        """Return statistics about the vector store collection."""


class ChromaVectorStore(VectorStoreBase):
    """ChromaDB-backed vector store with hybrid search support."""

    COLLECTION_NAME = "financial_documents"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("chroma_initialized", path=settings.chroma_persist_directory)

    async def add_chunks(
        self, chunks: list[DocumentChunk], embeddings: list[list[float]]
    ) -> int:
        if not chunks:
            return 0

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "company_name": chunk.metadata.company_name,
                "ticker": chunk.metadata.ticker,
                "filing_type": chunk.metadata.filing_type.value
                if hasattr(chunk.metadata.filing_type, "value")
                else str(chunk.metadata.filing_type),
                "section": chunk.metadata.section,
                "filing_date": chunk.metadata.filing_date,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("chunks_stored", count=len(chunks))
            return len(chunks)
        except Exception as e:
            raise RetrievalError(f"Failed to store chunks in ChromaDB: {e}") from e

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        where_filter = self._build_where_filter(metadata_filter)

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            raise RetrievalError(f"ChromaDB search failed: {e}") from e

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        search_results: list[dict[str, Any]] = []
        for i, chunk_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0.0
            # ChromaDB cosine distance: lower = more similar. Convert to similarity.
            similarity = 1.0 - distance

            search_results.append({
                "chunk_id": chunk_id,
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "relevance_score": similarity,
            })

        return search_results

    async def keyword_search(
        self,
        query_text: str,
        top_k: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Sparse keyword-based search using ChromaDB's where_document filter."""
        where_filter = self._build_where_filter(metadata_filter)

        try:
            # Use ChromaDB's document content filter for keyword matching
            results = self._collection.get(
                where=where_filter if where_filter else None,
                where_document={"$contains": query_text.lower()},
                include=["documents", "metadatas"],
                limit=top_k,
            )
        except Exception as e:
            raise RetrievalError(f"Keyword search failed: {e}") from e

        if not results or not results["ids"]:
            return []

        return [
            {
                "chunk_id": results["ids"][i],
                "content": results["documents"][i] if results["documents"] else "",
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
                "relevance_score": 0.5,  # keyword matches get base score
            }
            for i in range(len(results["ids"]))
        ]

    async def delete_by_document_id(self, document_id: str) -> int:
        try:
            existing = self._collection.get(
                where={"document_id": document_id},
            )
            if existing["ids"]:
                self._collection.delete(ids=existing["ids"])
                return len(existing["ids"])
            return 0
        except Exception as e:
            raise RetrievalError(f"Delete failed: {e}") from e

    async def get_collection_stats(self) -> dict[str, Any]:
        count = self._collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.COLLECTION_NAME,
            "provider": "chromadb",
        }

    @staticmethod
    def _build_where_filter(metadata_filter: dict[str, Any] | None) -> dict[str, Any] | None:
        if not metadata_filter:
            return None

        conditions: list[dict[str, Any]] = []
        for key, value in metadata_filter.items():
            if value is not None and value != "":
                conditions.append({key: {"$eq": value}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}


def create_vector_store() -> VectorStoreBase:
    """Factory function to create the configured vector store."""
    settings = get_settings()
    if settings.vector_store_provider == VectorStoreProvider.CHROMA:
        return ChromaVectorStore()
    raise ValueError(f"Unsupported vector store: {settings.vector_store_provider}")
