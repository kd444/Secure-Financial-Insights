"""Unified evaluation pipeline orchestrating all quality checks.

Combines hallucination detection, consistency scoring, and confidence
scoring into a single evaluation result with a pass/flag/fail verdict.
"""

from __future__ import annotations

from src.core.config import get_settings
from src.core.logging import get_logger
from src.evaluation.confidence_scorer import ConfidenceScorer
from src.evaluation.consistency_scorer import ConsistencyScorer
from src.evaluation.hallucination_detector import HallucinationDetector
from src.llm.client import LLMClient
from src.models.schemas import Citation, EvaluationResult, EvaluationStatus
from src.monitoring.metrics import (
    EVALUATION_SCORES,
    EVALUATION_STATUS_COUNTER,
)
from src.rag.embeddings import EmbeddingService

logger = get_logger(__name__)


class EvaluationPipeline:
    """Orchestrates the full LLM output evaluation pipeline.

    Pipeline stages:
    1. Hallucination detection (claim-level verification)
    2. Self-consistency scoring (multi-sample comparison)
    3. Confidence scoring (composite quality signal)
    4. Final verdict determination (pass/flag/fail)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        embedding_service: EmbeddingService,
    ) -> None:
        self._hallucination_detector = HallucinationDetector(llm_client, embedding_service)
        self._consistency_scorer = ConsistencyScorer(llm_client)
        self._confidence_scorer = ConfidenceScorer()
        self._settings = get_settings()

    async def evaluate(
        self,
        response_text: str,
        source_chunks: list[str],
        query: str,
        citations: list[Citation],
        messages: list[dict[str, str]] | None = None,
        run_consistency: bool = True,
    ) -> EvaluationResult:
        """Run full evaluation pipeline on an LLM response.

        Args:
            response_text: The generated response text.
            source_chunks: Source document chunks used for generation.
            query: The original user query.
            citations: Citations from retrieval.
            messages: Original prompt messages (needed for consistency check).
            run_consistency: Whether to run the expensive consistency check.

        Returns:
            EvaluationResult with scores and verdict.
        """
        flags: list[str] = []

        # Stage 1: Hallucination detection
        hallucination = await self._hallucination_detector.detect(
            response_text, source_chunks, query
        )

        if hallucination.hallucination_score > self._settings.hallucination_threshold:
            flags.append(
                f"High hallucination score: {hallucination.hallucination_score:.2f}"
            )

        # Stage 2: Consistency scoring (optional, expensive)
        consistency_score = 1.0
        if run_consistency and messages:
            consistency = await self._consistency_scorer.score(
                original_response=response_text,
                messages=messages,
                query=query,
            )
            consistency_score = consistency.consistency_score

            if consistency_score < self._settings.consistency_threshold:
                flags.append(
                    f"Low consistency score: {consistency_score:.2f}"
                )

        # Stage 3: Confidence scoring
        confidence = self._confidence_scorer.score(
            response_text=response_text,
            query=query,
            citations=citations,
            source_chunks=source_chunks,
            hallucination_score=hallucination.hallucination_score,
            consistency_score=consistency_score,
        )

        if confidence.confidence_score < self._settings.min_confidence_score:
            flags.append(
                f"Low confidence score: {confidence.confidence_score:.2f}"
            )

        # Stage 4: Determine verdict
        status = self._determine_status(
            hallucination.hallucination_score,
            consistency_score,
            confidence.confidence_score,
            flags,
        )

        # Build reasoning summary
        reasoning = (
            f"Hallucination: {hallucination.hallucination_score:.3f} "
            f"(entity overlap: {hallucination.entity_overlap_score:.3f}, "
            f"semantic sim: {hallucination.semantic_similarity_score:.3f}). "
            f"Consistency: {consistency_score:.3f}. "
            f"Confidence: {confidence.confidence_score:.3f} "
            f"(citations: {confidence.citation_density_score:.3f}, "
            f"specificity: {confidence.specificity_score:.3f}). "
            f"{hallucination.reasoning}"
        )

        result = EvaluationResult(
            hallucination_score=hallucination.hallucination_score,
            factual_grounding_score=hallucination.factual_grounding_score,
            semantic_consistency_score=consistency_score,
            confidence_score=confidence.confidence_score,
            status=status,
            flags=flags,
            evaluation_reasoning=reasoning,
        )

        # Track metrics
        EVALUATION_SCORES.labels(metric="hallucination").observe(
            hallucination.hallucination_score
        )
        EVALUATION_SCORES.labels(metric="consistency").observe(consistency_score)
        EVALUATION_SCORES.labels(metric="confidence").observe(
            confidence.confidence_score
        )
        EVALUATION_STATUS_COUNTER.labels(status=status.value).inc()

        logger.info(
            "evaluation_complete",
            status=status.value,
            hallucination=hallucination.hallucination_score,
            consistency=consistency_score,
            confidence=confidence.confidence_score,
            flags=flags,
        )

        return result

    def _determine_status(
        self,
        hallucination_score: float,
        consistency_score: float,
        confidence_score: float,
        flags: list[str],
    ) -> EvaluationStatus:
        """Determine pass/flag/fail status based on thresholds."""
        # Hard fail: high hallucination
        if hallucination_score > 0.8:
            return EvaluationStatus.FAILED

        # Fail: multiple quality issues
        if len(flags) >= 3:
            return EvaluationStatus.FAILED

        # Flag: any quality concern
        if flags:
            return EvaluationStatus.FLAGGED

        # Pass: all scores within acceptable range
        if (
            hallucination_score <= self._settings.hallucination_threshold
            and consistency_score >= self._settings.consistency_threshold
            and confidence_score >= self._settings.min_confidence_score
        ):
            return EvaluationStatus.PASSED

        return EvaluationStatus.FLAGGED
