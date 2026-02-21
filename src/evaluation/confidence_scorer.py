"""Confidence scoring for LLM-generated financial analysis.

Computes a composite confidence score based on:
1. Source coverage: How well the query is covered by retrieved documents
2. Response quality signals: Citation density, hedging language, specificity
3. Retrieval relevance: Average relevance score of retrieved chunks
4. Model certainty: Based on evaluation results
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.logging import get_logger
from src.models.schemas import Citation

logger = get_logger(__name__)

# Hedging phrases that indicate lower confidence
HEDGING_PHRASES = [
    "it is possible that",
    "may have",
    "could potentially",
    "it appears that",
    "it seems",
    "approximately",
    "roughly",
    "unclear",
    "not enough information",
    "limited data",
    "cannot determine",
    "uncertain",
    "speculative",
]

# Confidence-boosting signals
HIGH_CONFIDENCE_SIGNALS = [
    r"\[Source \d+\]",  # Citations present
    r"\$[\d,]+",  # Specific dollar amounts
    r"\d+\.?\d*%",  # Specific percentages
    r"(?:Q[1-4]|FY)\s*\d{4}",  # Specific time periods
    r"(?:increased|decreased|grew|declined)\s+(?:by\s+)?\d",  # Quantified changes
]


@dataclass
class ConfidenceResult:
    confidence_score: float  # 0.0 = no confidence, 1.0 = full confidence
    source_coverage_score: float
    citation_density_score: float
    specificity_score: float
    hedging_penalty: float
    retrieval_relevance_score: float
    breakdown: dict[str, float]


class ConfidenceScorer:
    """Scores confidence of an LLM response based on multiple quality signals."""

    def score(
        self,
        response_text: str,
        query: str,
        citations: list[Citation],
        source_chunks: list[str],
        hallucination_score: float = 0.0,
        consistency_score: float = 1.0,
    ) -> ConfidenceResult:
        """Compute composite confidence score.

        Args:
            response_text: The generated response.
            query: Original user query.
            citations: Retrieved citations.
            source_chunks: Source document chunks.
            hallucination_score: From hallucination detector (0=clean, 1=hallucinated).
            consistency_score: From consistency scorer.

        Returns:
            ConfidenceResult with composite and component scores.
        """
        # Component scores
        source_coverage = self._score_source_coverage(query, source_chunks)
        citation_density = self._score_citation_density(response_text)
        specificity = self._score_specificity(response_text)
        hedging = self._score_hedging_penalty(response_text)
        retrieval_relevance = self._score_retrieval_relevance(citations)

        # Composite score with weights
        composite = (
            0.20 * source_coverage
            + 0.15 * citation_density
            + 0.10 * specificity
            + 0.15 * (1.0 - hedging)  # hedging reduces confidence
            + 0.10 * retrieval_relevance
            + 0.15 * (1.0 - hallucination_score)  # low hallucination = high confidence
            + 0.15 * consistency_score
        )

        result = ConfidenceResult(
            confidence_score=round(min(max(composite, 0.0), 1.0), 4),
            source_coverage_score=round(source_coverage, 4),
            citation_density_score=round(citation_density, 4),
            specificity_score=round(specificity, 4),
            hedging_penalty=round(hedging, 4),
            retrieval_relevance_score=round(retrieval_relevance, 4),
            breakdown={
                "source_coverage": round(source_coverage, 4),
                "citation_density": round(citation_density, 4),
                "specificity": round(specificity, 4),
                "hedging_penalty": round(hedging, 4),
                "retrieval_relevance": round(retrieval_relevance, 4),
                "hallucination_factor": round(1.0 - hallucination_score, 4),
                "consistency_factor": round(consistency_score, 4),
            },
        )

        logger.info(
            "confidence_scored",
            score=result.confidence_score,
            source_coverage=source_coverage,
            citation_density=citation_density,
        )

        return result

    def _score_source_coverage(self, query: str, source_chunks: list[str]) -> float:
        """How well do the source documents cover the query topic?"""
        if not source_chunks:
            return 0.0

        query_terms = set(query.lower().split())
        query_terms -= {"what", "how", "why", "when", "is", "the", "a", "an", "of", "in", "for"}

        if not query_terms:
            return 0.5

        combined_sources = " ".join(source_chunks).lower()
        matched = sum(1 for term in query_terms if term in combined_sources)
        return matched / len(query_terms)

    def _score_citation_density(self, response_text: str) -> float:
        """Score based on how many citations appear relative to response length."""
        citation_count = len(re.findall(r"\[Source \d+\]", response_text))
        # Rough heuristic: ~1 citation per 100 words is good
        word_count = len(response_text.split())
        if word_count == 0:
            return 0.0

        expected_citations = max(1, word_count / 100)
        ratio = citation_count / expected_citations
        return min(ratio, 1.0)

    def _score_specificity(self, response_text: str) -> float:
        """Score based on presence of specific data points (numbers, dates, figures)."""
        signal_count = 0
        for pattern in HIGH_CONFIDENCE_SIGNALS:
            matches = re.findall(pattern, response_text)
            signal_count += len(matches)

        # Normalize: 5+ specific data points = full score
        return min(signal_count / 5.0, 1.0)

    def _score_hedging_penalty(self, response_text: str) -> float:
        """Score penalty for hedging language (higher = more hedging = less confident)."""
        text_lower = response_text.lower()
        hedge_count = sum(1 for phrase in HEDGING_PHRASES if phrase in text_lower)

        # Normalize: 3+ hedging phrases = max penalty
        return min(hedge_count / 3.0, 1.0)

    def _score_retrieval_relevance(self, citations: list[Citation]) -> float:
        """Average relevance score from retrieved citations."""
        if not citations:
            return 0.0
        avg = sum(c.relevance_score for c in citations) / len(citations)
        return min(max(avg, 0.0), 1.0)
