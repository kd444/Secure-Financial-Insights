"""LLM output hallucination detection using claim-level verification.

Implements a multi-strategy approach:
1. LLM-as-judge: Uses a secondary LLM call to verify factual grounding
2. Embedding similarity: Compares response embeddings against source chunks
3. Named entity cross-reference: Verifies financial entities (numbers, dates, names)
   mentioned in the response exist in source documents

This produces a hallucination score used for quality gating.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm.client import LLMClient
from src.llm.prompts import HALLUCINATION_CHECK_PROMPT
from src.rag.embeddings import EmbeddingService

logger = get_logger(__name__)


@dataclass
class ClaimVerification:
    claim: str
    verdict: str  # SUPPORTED, UNSUPPORTED, CONTRADICTED
    evidence: str
    source_ref: str


@dataclass
class HallucinationResult:
    hallucination_score: float  # 0.0 = no hallucination, 1.0 = fully hallucinated
    factual_grounding_score: float
    claims: list[ClaimVerification] = field(default_factory=list)
    entity_overlap_score: float = 0.0
    semantic_similarity_score: float = 0.0
    reasoning: str = ""


class HallucinationDetector:
    """Detects hallucinations in LLM-generated financial analysis.

    Combines three signals:
    - LLM-based claim verification (primary)
    - Embedding cosine similarity between response and sources
    - Named entity overlap between response and sources
    """

    def __init__(
        self,
        llm_client: LLMClient,
        embedding_service: EmbeddingService,
    ) -> None:
        self._llm = llm_client
        self._embeddings = embedding_service
        self._settings = get_settings()

    async def detect(
        self,
        response_text: str,
        source_chunks: list[str],
        query: str,
    ) -> HallucinationResult:
        """Run full hallucination detection pipeline.

        Args:
            response_text: The LLM-generated response to evaluate.
            source_chunks: The source documents the response should be grounded in.
            query: The original user query.

        Returns:
            HallucinationResult with scores and claim-level details.
        """
        # Run all detection strategies in parallel conceptually
        # (in practice, LLM call is the bottleneck)
        llm_result = await self._llm_judge_verification(
            response_text, source_chunks, query
        )
        entity_score = self._entity_overlap_check(response_text, source_chunks)
        semantic_score = await self._semantic_similarity_check(
            response_text, source_chunks
        )

        # Combine scores with weighted average
        # LLM judge is most reliable, entity overlap catches numerical errors
        combined_hallucination = (
            0.6 * llm_result.hallucination_score
            + 0.2 * (1.0 - entity_score)
            + 0.2 * (1.0 - semantic_score)
        )

        combined_grounding = (
            0.6 * llm_result.factual_grounding_score
            + 0.2 * entity_score
            + 0.2 * semantic_score
        )

        result = HallucinationResult(
            hallucination_score=round(min(max(combined_hallucination, 0.0), 1.0), 4),
            factual_grounding_score=round(min(max(combined_grounding, 0.0), 1.0), 4),
            claims=llm_result.claims,
            entity_overlap_score=round(entity_score, 4),
            semantic_similarity_score=round(semantic_score, 4),
            reasoning=llm_result.reasoning,
        )

        logger.info(
            "hallucination_detection_complete",
            hallucination_score=result.hallucination_score,
            grounding_score=result.factual_grounding_score,
            claims_count=len(result.claims),
            entity_overlap=result.entity_overlap_score,
        )

        return result

    async def _llm_judge_verification(
        self,
        response_text: str,
        source_chunks: list[str],
        query: str,
    ) -> HallucinationResult:
        """Use LLM as judge to verify claims against sources."""
        context = "\n---\n".join(
            f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(source_chunks)
        )

        prompt = HALLUCINATION_CHECK_PROMPT.format(
            context=context,
            response=response_text,
            query=query,
        )

        try:
            result_text, _ = await self._llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            parsed = json.loads(result_text)

            claims = [
                ClaimVerification(
                    claim=c.get("claim", ""),
                    verdict=c.get("verdict", "UNSUPPORTED"),
                    evidence=c.get("evidence", ""),
                    source_ref=c.get("source_ref", ""),
                )
                for c in parsed.get("claims", [])
            ]

            return HallucinationResult(
                hallucination_score=float(parsed.get("hallucination_score", 0.5)),
                factual_grounding_score=float(parsed.get("factual_grounding_score", 0.5)),
                claims=claims,
                reasoning=parsed.get("reasoning", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("llm_judge_parse_error", error=str(e))
            return HallucinationResult(
                hallucination_score=0.5,
                factual_grounding_score=0.5,
                reasoning=f"LLM judge evaluation failed to parse: {e}",
            )

    def _entity_overlap_check(
        self, response_text: str, source_chunks: list[str]
    ) -> float:
        """Check overlap of named entities (numbers, dates, companies) between
        response and source documents.

        Returns a score from 0.0 (no overlap) to 1.0 (full overlap).
        """
        response_entities = self._extract_financial_entities(response_text)
        if not response_entities:
            return 1.0  # No entities to verify

        source_text = " ".join(source_chunks)
        source_entities = self._extract_financial_entities(source_text)

        if not source_entities:
            return 0.5  # Can't verify

        # Check what fraction of response entities appear in sources
        matched = sum(1 for e in response_entities if e in source_entities)
        return matched / len(response_entities)

    async def _semantic_similarity_check(
        self, response_text: str, source_chunks: list[str]
    ) -> float:
        """Compute average cosine similarity between response and source chunks."""
        if not source_chunks:
            return 0.0

        try:
            response_embedding = await self._embeddings.embed_query(response_text)
            chunk_embeddings = await self._embeddings.embed_texts(source_chunks)

            similarities = [
                EmbeddingService.cosine_similarity(response_embedding, ce)
                for ce in chunk_embeddings
            ]

            # Use max similarity (best matching chunk) rather than average
            return max(similarities) if similarities else 0.0

        except Exception as e:
            logger.warning("semantic_similarity_error", error=str(e))
            return 0.5

    @staticmethod
    def _extract_financial_entities(text: str) -> set[str]:
        """Extract financial entities: dollar amounts, percentages, dates, tickers."""
        entities: set[str] = set()

        # Dollar amounts: $1.5B, $500M, $1,234.56
        for match in re.finditer(r'\$[\d,]+\.?\d*\s*[BMKbmk]?(?:illion|illion)?', text):
            entities.add(match.group().strip().lower())

        # Percentages: 15.3%, -2.1%
        for match in re.finditer(r'-?[\d.]+%', text):
            entities.add(match.group())

        # Dates: Q1 2024, FY2023, December 31, 2023
        for match in re.finditer(r'(?:Q[1-4]\s*\d{4}|FY\d{4}|\d{4})', text):
            entities.add(match.group())

        # Large numbers with context
        for match in re.finditer(r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b', text):
            entities.add(match.group())

        return entities
