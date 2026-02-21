"""Semantic consistency scoring via self-consistency checking.

Implements the self-consistency technique: generates multiple responses
to the same query and measures agreement between them. High consistency
indicates the model is confident and grounded; low consistency flags
potential hallucination or ambiguity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.core.logging import get_logger
from src.llm.client import LLMClient
from src.llm.prompts import CONSISTENCY_CHECK_PROMPT

logger = get_logger(__name__)

DEFAULT_NUM_SAMPLES = 2  # Number of additional samples for self-consistency


@dataclass
class ConsistencyResult:
    consistency_score: float  # 0.0 = inconsistent, 1.0 = fully consistent
    num_samples: int
    discrepancies: list[str]
    reasoning: str


class ConsistencyScorer:
    """Evaluates response consistency by comparing multiple LLM generations.

    Self-consistency check:
    1. Generate N additional responses to the same prompt
    2. Compare each pair using LLM-based semantic comparison
    3. Aggregate pairwise consistency scores

    High consistency (>0.8) suggests factual grounding.
    Low consistency (<0.5) suggests the model is uncertain or hallucinating.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def score(
        self,
        original_response: str,
        messages: list[dict[str, str]],
        query: str,
        num_samples: int = DEFAULT_NUM_SAMPLES,
    ) -> ConsistencyResult:
        """Score the consistency of a response via self-consistency sampling.

        Args:
            original_response: The primary response to evaluate.
            messages: The original prompt messages used to generate the response.
            query: The user's original query.
            num_samples: Number of additional samples to generate.

        Returns:
            ConsistencyResult with aggregate score and discrepancy details.
        """
        # Generate additional samples with slightly higher temperature
        alternative_responses: list[str] = []
        for _ in range(num_samples):
            try:
                alt_response, _ = await self._llm.generate(
                    messages=messages,
                    temperature=0.3,  # slightly more variation
                )
                alternative_responses.append(alt_response)
            except Exception as e:
                logger.warning("consistency_sample_failed", error=str(e))

        if not alternative_responses:
            return ConsistencyResult(
                consistency_score=0.5,  # uncertain
                num_samples=0,
                discrepancies=["Failed to generate comparison samples"],
                reasoning="Could not generate alternative responses for comparison",
            )

        # Compare original with each alternative
        pairwise_scores: list[float] = []
        all_discrepancies: list[str] = []

        for alt_response in alternative_responses:
            pair_result = await self._compare_pair(
                query, original_response, alt_response
            )
            pairwise_scores.append(pair_result["score"])
            all_discrepancies.extend(pair_result["discrepancies"])

        avg_score = sum(pairwise_scores) / len(pairwise_scores)

        result = ConsistencyResult(
            consistency_score=round(avg_score, 4),
            num_samples=len(alternative_responses),
            discrepancies=all_discrepancies,
            reasoning=f"Compared with {len(alternative_responses)} alternative responses. "
            f"Pairwise scores: {[round(s, 3) for s in pairwise_scores]}",
        )

        logger.info(
            "consistency_scoring_complete",
            score=result.consistency_score,
            num_samples=result.num_samples,
            discrepancies_count=len(result.discrepancies),
        )

        return result

    async def _compare_pair(
        self, query: str, response_a: str, response_b: str
    ) -> dict[str, any]:
        """Compare two responses for semantic consistency using LLM judge."""
        prompt = CONSISTENCY_CHECK_PROMPT.format(
            query=query,
            response_a=response_a,
            response_b=response_b,
        )

        try:
            result_text, _ = await self._llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            parsed = json.loads(result_text)
            return {
                "score": float(parsed.get("consistency_score", 0.5)),
                "discrepancies": parsed.get("discrepancies", []),
            }

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("consistency_comparison_parse_error", error=str(e))
            return {"score": 0.5, "discrepancies": [f"Parse error: {e}"]}
