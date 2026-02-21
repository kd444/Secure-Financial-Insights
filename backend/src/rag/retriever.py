"""Hybrid retriever with reranking and citation injection.

Combines semantic (dense) and keyword (sparse) retrieval with
reciprocal rank fusion (RRF) for optimal recall on financial queries.
Injects source citations for every retrieved chunk.
"""

from __future__ import annotations

from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.schemas import Citation
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import ChromaVectorStore, VectorStoreBase

logger = get_logger(__name__)


class HybridRetriever:
    """Retrieves relevant document chunks using hybrid dense+sparse search.

    Pipeline:
    1. Generate query embedding (dense)
    2. Run semantic search against vector store
    3. Run keyword search for exact financial terms
    4. Fuse results using Reciprocal Rank Fusion (RRF)
    5. Rerank by combined score
    6. Inject citations with source metadata
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreBase,
    ) -> None:
        self._embeddings = embedding_service
        self._vector_store = vector_store
        settings = get_settings()
        self._top_k = settings.retrieval_top_k
        self._rerank_top_k = settings.rerank_top_k
        self._alpha = settings.hybrid_search_alpha

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], list[Citation]]:
        """Retrieve relevant chunks with citations.

        Args:
            query: User query string.
            top_k: Number of results to return (overrides config).
            metadata_filter: Optional filters (ticker, filing_type, etc.).

        Returns:
            Tuple of (retrieved_chunks, citations).
        """
        top_k = top_k or self._top_k

        # Step 1: Generate query embedding
        query_embedding = await self._embeddings.embed_query(query)

        # Step 2: Semantic search (dense retrieval)
        semantic_results = await self._vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # over-fetch for fusion
            metadata_filter=metadata_filter,
        )

        # Step 3: Keyword search (sparse retrieval) - extract key terms
        keyword_results: list[dict[str, Any]] = []
        if isinstance(self._vector_store, ChromaVectorStore):
            key_terms = self._extract_key_terms(query)
            for term in key_terms[:3]:
                try:
                    results = await self._vector_store.keyword_search(
                        query_text=term,
                        top_k=top_k,
                        metadata_filter=metadata_filter,
                    )
                    keyword_results.extend(results)
                except Exception:
                    pass  # keyword search is best-effort

        # Step 4: Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            alpha=self._alpha,
        )

        # Step 5: Take top-k after fusion
        final_results = fused[: self._rerank_top_k or top_k]

        # Step 6: Build citations
        citations = self._build_citations(final_results)

        logger.info(
            "retrieval_complete",
            query_length=len(query),
            semantic_hits=len(semantic_results),
            keyword_hits=len(keyword_results),
            fused_results=len(final_results),
        )

        return final_results, citations

    def _reciprocal_rank_fusion(
        self,
        semantic: list[dict[str, Any]],
        keyword: list[dict[str, Any]],
        alpha: float = 0.7,
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """Combine semantic and keyword results using RRF.

        RRF score = alpha * (1 / (k + rank_semantic)) + (1-alpha) * (1 / (k + rank_keyword))

        Args:
            semantic: Semantic search results sorted by relevance.
            keyword: Keyword search results.
            alpha: Weight for semantic results (0-1).
            k: RRF constant (default 60).

        Returns:
            Fused and re-sorted results.
        """
        scores: dict[str, float] = {}
        chunk_map: dict[str, dict[str, Any]] = {}

        # Score semantic results
        for rank, result in enumerate(semantic):
            chunk_id = result["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + alpha / (k + rank + 1)
            chunk_map[chunk_id] = result

        # Score keyword results
        for rank, result in enumerate(keyword):
            chunk_id = result["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + (1 - alpha) / (k + rank + 1)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = result

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_results: list[dict[str, Any]] = []
        for chunk_id in sorted_ids:
            result = chunk_map[chunk_id].copy()
            result["rrf_score"] = scores[chunk_id]
            fused_results.append(result)

        return fused_results

    def _build_citations(self, results: list[dict[str, Any]]) -> list[Citation]:
        """Build structured citations from retrieval results."""
        citations: list[Citation] = []
        for result in results:
            metadata = result.get("metadata", {})
            content = result.get("content", "")

            # Create a concise excerpt (first 200 chars)
            excerpt = content[:200].strip()
            if len(content) > 200:
                excerpt += "..."

            citation = Citation(
                chunk_id=result["chunk_id"],
                source_document=(
                    f"{metadata.get('company_name', 'Unknown')} "
                    f"{metadata.get('filing_type', '')} "
                    f"{metadata.get('filing_date', '')}"
                ).strip(),
                section=metadata.get("section", ""),
                relevance_score=result.get("rrf_score", result.get("relevance_score", 0.0)),
                text_excerpt=excerpt,
            )
            citations.append(citation)

        return citations

    @staticmethod
    def _extract_key_terms(query: str) -> list[str]:
        """Extract financially-relevant key terms from query for keyword search.

        Focuses on proper nouns, financial terms, and numbers that are
        important for exact matching in financial documents.
        """
        # Financial terms that should be matched exactly
        financial_terms = {
            "revenue", "earnings", "ebitda", "eps", "net income", "gross margin",
            "operating income", "free cash flow", "debt", "equity", "assets",
            "liabilities", "dividend", "buyback", "guidance", "outlook",
            "risk factor", "litigation", "regulatory", "compliance",
            "market cap", "p/e ratio", "roi", "roa", "roe",
        }

        query_lower = query.lower()
        found_terms: list[str] = []

        for term in financial_terms:
            if term in query_lower:
                found_terms.append(term)

        # Also extract potential ticker symbols (1-5 uppercase letters)
        import re
        tickers = re.findall(r'\b[A-Z]{1,5}\b', query)
        found_terms.extend(tickers)

        # Extract numbers and percentages (important in financial context)
        numbers = re.findall(r'\$?[\d,]+\.?\d*%?', query)
        found_terms.extend(numbers)

        return found_terms
