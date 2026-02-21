"""LLM evaluation test suite using predefined test cases.

These tests verify that the evaluation pipeline correctly identifies:
- Hallucinated responses (claims not in sources)
- Grounded responses (claims supported by sources)
- Confidence scoring accuracy

These can be run with the 'evaluation' pytest marker:
    pytest -m evaluation
"""

import pytest

from src.evaluation.confidence_scorer import ConfidenceScorer
from src.models.schemas import Citation


# === Test Fixtures: Golden Evaluation Cases ===

GROUNDED_CASE = {
    "query": "What was Apple's revenue in FY2023?",
    "source_chunks": [
        "[Apple Inc. (AAPL) | 10-K | Item 7 - MDA]\n\n"
        "Total net revenue for fiscal year 2023 was $394.3 billion, "
        "an increase of 8% compared to $365.8 billion in 2022. "
        "Products revenue was $298.1 billion. Services revenue was "
        "$85.2 billion, growing 16% year-over-year.",
    ],
    "response": (
        "According to [Source 1], Apple's total net revenue for FY2023 "
        "was $394.3 billion, representing an 8% increase from $365.8 "
        "billion in FY2022. Products contributed $298.1 billion while "
        "Services grew 16% to $85.2 billion [Source 1]."
    ),
    "expected_grounded": True,
}

HALLUCINATED_CASE = {
    "query": "What was Apple's revenue in FY2023?",
    "source_chunks": [
        "Total net revenue for fiscal year 2023 was $394.3 billion.",
    ],
    "response": (
        "Apple's revenue in FY2023 was $450 billion, making it the "
        "first company to reach this milestone. CEO Tim Cook announced "
        "a special dividend of $10 per share to celebrate."
    ),
    "expected_grounded": False,
}


@pytest.mark.evaluation
class TestEvaluationGoldenCases:
    """Golden test cases for the evaluation pipeline.

    These test known-good and known-bad responses to verify
    the evaluation scoring works correctly on deterministic inputs.
    """

    def test_confidence_scores_grounded_higher(self):
        scorer = ConfidenceScorer()

        grounded_result = scorer.score(
            response_text=GROUNDED_CASE["response"],
            query=GROUNDED_CASE["query"],
            citations=[
                Citation(
                    chunk_id="1",
                    source_document="Apple 10-K",
                    section="MDA",
                    relevance_score=0.95,
                    text_excerpt="Revenue was $394.3B",
                )
            ],
            source_chunks=GROUNDED_CASE["source_chunks"],
            hallucination_score=0.1,
            consistency_score=0.9,
        )

        hallucinated_result = scorer.score(
            response_text=HALLUCINATED_CASE["response"],
            query=HALLUCINATED_CASE["query"],
            citations=[
                Citation(
                    chunk_id="1",
                    source_document="Apple 10-K",
                    section="MDA",
                    relevance_score=0.95,
                    text_excerpt="Revenue was $394.3B",
                )
            ],
            source_chunks=HALLUCINATED_CASE["source_chunks"],
            hallucination_score=0.8,
            consistency_score=0.3,
        )

        assert grounded_result.confidence_score > hallucinated_result.confidence_score

    def test_citation_density_grounded_response(self):
        scorer = ConfidenceScorer()
        result = scorer.score(
            response_text=GROUNDED_CASE["response"],
            query=GROUNDED_CASE["query"],
            citations=[],
            source_chunks=GROUNDED_CASE["source_chunks"],
        )
        assert result.citation_density_score > 0.0

    def test_no_citations_in_hallucinated(self):
        scorer = ConfidenceScorer()
        result = scorer.score(
            response_text=HALLUCINATED_CASE["response"],
            query=HALLUCINATED_CASE["query"],
            citations=[],
            source_chunks=HALLUCINATED_CASE["source_chunks"],
        )
        assert result.citation_density_score == 0.0

    def test_specificity_with_numbers(self):
        scorer = ConfidenceScorer()
        specific = "Revenue was $394.3 billion in FY2023, up 8% [Source 1]."
        vague = "Revenue was high and grew somewhat."

        result_specific = scorer.score(specific, "revenue", [], ["revenue"])
        result_vague = scorer.score(vague, "revenue", [], ["revenue"])

        assert result_specific.specificity_score > result_vague.specificity_score
