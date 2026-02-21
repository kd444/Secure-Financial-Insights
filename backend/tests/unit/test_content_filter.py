"""Unit tests for the content filtering guardrails."""

import pytest

from src.guardrails.content_filter import ContentFilter, ViolationType


@pytest.fixture
def content_filter():
    return ContentFilter()


class TestContentFilter:
    def test_clean_content_passes(self, content_filter):
        text = (
            "Based on the 10-K filing [Source 1], Apple's revenue increased "
            "8% year-over-year to $394.3 billion. Services grew 16% to "
            "$85.2 billion."
        )
        result = content_filter.filter(text)
        assert result.passed
        assert len(result.violations) == 0

    def test_investment_advice_blocked(self, content_filter):
        text = "Based on strong fundamentals, you should buy AAPL stock immediately."
        result = content_filter.filter(text)
        blocked = [v for v in result.violations if v.severity == "block"]
        assert len(blocked) > 0
        assert any(
            v.violation_type == ViolationType.INVESTMENT_ADVICE
            for v in result.violations
        )

    def test_strong_buy_recommendation_blocked(self, content_filter):
        text = "We give AAPL a strong buy rating with a target price of $250."
        result = content_filter.filter(text)
        assert any(
            v.violation_type == ViolationType.INVESTMENT_ADVICE
            for v in result.violations
        )

    def test_forward_looking_statements_flagged(self, content_filter):
        text = "Revenue is expected to increase significantly in the next quarter."
        result = content_filter.filter(text)
        assert any(
            v.violation_type == ViolationType.FORWARD_LOOKING
            for v in result.violations
        )

    def test_forward_looking_adds_disclaimer(self, content_filter):
        text = "The company's future revenue growth is projected to be 15%."
        result = content_filter.filter(text)
        assert "forward-looking statements" in result.filtered_text.lower()

    def test_multiple_violations(self, content_filter):
        text = (
            "Revenue will likely increase next year. "
            "We recommend you should buy this stock."
        )
        result = content_filter.filter(text)
        assert len(result.violations) >= 2

    def test_factual_financial_content_passes(self, content_filter):
        text = (
            "According to the Q3 2023 10-Q filing [Source 1], "
            "net income was $22.9 billion, representing a 10.8% "
            "net margin. Operating cash flow was $29.5 billion."
        )
        result = content_filter.filter(text)
        assert result.passed
