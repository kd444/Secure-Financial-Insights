"""Unit tests for Pydantic schemas and validation."""

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    DocumentMetadata,
    EvaluationResult,
    EvaluationStatus,
    FilingType,
    QueryRequest,
    QueryResponse,
    QueryType,
)


class TestQueryRequest:
    def test_valid_request(self):
        req = QueryRequest(
            query="What are Apple's risk factors?",
            query_type=QueryType.RISK_SUMMARY,
            company_filter="AAPL",
        )
        assert req.query == "What are Apple's risk factors?"
        assert req.query_type == QueryType.RISK_SUMMARY

    def test_query_too_short_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="Hi")

    def test_default_values(self):
        req = QueryRequest(query="What is the revenue?")
        assert req.query_type == QueryType.GENERAL
        assert req.top_k == 5
        assert req.include_evaluation is True
        assert req.stream is False

    def test_top_k_validation(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="Test query here", top_k=0)
        with pytest.raises(ValidationError):
            QueryRequest(query="Test query here", top_k=25)


class TestEvaluationResult:
    def test_valid_evaluation(self):
        result = EvaluationResult(
            hallucination_score=0.1,
            factual_grounding_score=0.9,
            semantic_consistency_score=0.85,
            confidence_score=0.8,
            status=EvaluationStatus.PASSED,
        )
        assert result.status == EvaluationStatus.PASSED

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            EvaluationResult(
                hallucination_score=1.5,  # out of bounds
                factual_grounding_score=0.9,
                semantic_consistency_score=0.85,
                confidence_score=0.8,
                status=EvaluationStatus.PASSED,
            )

    def test_flags_default_empty(self):
        result = EvaluationResult(
            hallucination_score=0.1,
            factual_grounding_score=0.9,
            semantic_consistency_score=0.85,
            confidence_score=0.8,
            status=EvaluationStatus.PASSED,
        )
        assert result.flags == []


class TestDocumentMetadata:
    def test_filing_types(self):
        for ft in FilingType:
            meta = DocumentMetadata(filing_type=ft)
            assert meta.filing_type == ft

    def test_default_values(self):
        meta = DocumentMetadata()
        assert meta.filing_type == FilingType.OTHER
        assert meta.company_name == ""
        assert meta.ticker == ""
