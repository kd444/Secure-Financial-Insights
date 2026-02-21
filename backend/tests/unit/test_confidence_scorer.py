"""Unit tests for the confidence scoring system."""

import pytest

from src.evaluation.confidence_scorer import ConfidenceScorer
from src.models.schemas import Citation


@pytest.fixture
def scorer():
    return ConfidenceScorer()


@pytest.fixture
def high_quality_response():
    return (
        "According to [Source 1], Apple's revenue increased 8% year-over-year "
        "to $394.3 billion in FY2023. The Services segment grew 16% to "
        "$85.2 billion [Source 2]. Gross margin improved to 45.2% from 43.3% "
        "[Source 1]. Operating expenses were $55.0 billion, representing a 5% "
        "increase [Source 3]."
    )


@pytest.fixture
def low_quality_response():
    return (
        "It seems like Apple may have had some revenue growth, possibly "
        "around some amount. It is possible that they did well, but it's "
        "unclear exactly how much. There isn't enough information to say."
    )


@pytest.fixture
def sample_citations():
    return [
        Citation(
            chunk_id="1",
            source_document="Apple 10-K 2024",
            section="MDA",
            relevance_score=0.92,
            text_excerpt="Revenue increased 8%...",
        ),
        Citation(
            chunk_id="2",
            source_document="Apple 10-K 2024",
            section="Financial Statements",
            relevance_score=0.88,
            text_excerpt="Services revenue was $85.2B...",
        ),
    ]


class TestConfidenceScorer:
    def test_high_quality_response_scores_high(
        self, scorer, high_quality_response, sample_citations
    ):
        result = scorer.score(
            response_text=high_quality_response,
            query="What was Apple's revenue in 2023?",
            citations=sample_citations,
            source_chunks=["Revenue increased 8% to $394.3 billion."],
        )
        assert result.confidence_score > 0.6

    def test_low_quality_response_scores_low(
        self, scorer, low_quality_response, sample_citations
    ):
        result = scorer.score(
            response_text=low_quality_response,
            query="What was Apple's revenue in 2023?",
            citations=sample_citations,
            source_chunks=["Revenue increased 8% to $394.3 billion."],
        )
        assert result.confidence_score < 0.6

    def test_citation_density_scoring(self, scorer, sample_citations):
        with_citations = "Revenue was $394B [Source 1]. Growth was 8% [Source 2]."
        without_citations = "Revenue was approximately some amount. Growth was notable."

        result_with = scorer.score(
            with_citations, "revenue", sample_citations, ["revenue"]
        )
        result_without = scorer.score(
            without_citations, "revenue", sample_citations, ["revenue"]
        )

        assert result_with.citation_density_score > result_without.citation_density_score

    def test_hedging_penalty(self, scorer, sample_citations):
        hedging = "It seems like it may have increased. It is possible that revenue grew."
        confident = "Revenue increased 8% to $394.3 billion in FY2023 [Source 1]."

        result_hedge = scorer.score(hedging, "revenue", sample_citations, ["revenue"])
        result_conf = scorer.score(confident, "revenue", sample_citations, ["revenue"])

        assert result_hedge.hedging_penalty > result_conf.hedging_penalty

    def test_empty_citations_low_retrieval_score(self, scorer):
        result = scorer.score("Some response", "query", [], ["source"])
        assert result.retrieval_relevance_score == 0.0

    def test_breakdown_contains_all_components(
        self, scorer, high_quality_response, sample_citations
    ):
        result = scorer.score(
            high_quality_response, "revenue", sample_citations, ["revenue"]
        )
        assert "source_coverage" in result.breakdown
        assert "citation_density" in result.breakdown
        assert "specificity" in result.breakdown
        assert "hedging_penalty" in result.breakdown
        assert "retrieval_relevance" in result.breakdown
