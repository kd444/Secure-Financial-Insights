"""Shared test fixtures and configuration."""

import os

import pytest

# Set test environment before importing application code
os.environ["APP_ENV"] = "development"
os.environ["OPENAI_API_KEY"] = "sk-test-key-not-real"
os.environ["PII_DETECTION_ENABLED"] = "true"
os.environ["CONTENT_FILTER_ENABLED"] = "true"
os.environ["PROMETHEUS_ENABLED"] = "false"


@pytest.fixture(scope="session")
def sample_sec_filing_text():
    """Sample SEC 10-K filing text for testing."""
    return """
    Item 1A - Risk Factors

    The following risk factors could materially affect our business, financial
    condition and results of operations. Revenue concentration in a limited number
    of products presents significant risk. Our total revenue for fiscal year 2023
    was $394.3 billion, with iPhone representing approximately 52% of total revenue.

    Economic conditions, including inflation and rising interest rates, could
    reduce consumer spending on our products. A 10% decline in iPhone sales would
    reduce total revenue by approximately $20.4 billion.

    Supply chain disruptions remain a key risk factor. We rely on single-source
    suppliers for certain components, and any disruption could delay product launches.

    Item 7 - Management's Discussion and Analysis of Financial Condition

    Revenue for fiscal year 2023 was $394.3 billion, an increase of 8% compared
    to $365.8 billion in fiscal year 2022. Products revenue was $298.1 billion,
    and Services revenue was $85.2 billion, growing 16% year-over-year.

    Gross margin increased to 45.2% from 43.3% in the prior year, driven by a
    favorable product mix and services growth. Operating expenses were $55.0 billion,
    an increase of 5% year-over-year.

    Net income was $97.0 billion, or $6.13 per diluted share, compared to
    $94.7 billion, or $5.89 per diluted share in the prior year.
    """


@pytest.fixture
def sample_query_context():
    """Sample query with context for testing RAG pipeline."""
    return {
        "query": "What was Apple's revenue growth in FY2023?",
        "chunks": [
            "Revenue for fiscal year 2023 was $394.3 billion, an increase of "
            "8% compared to $365.8 billion in fiscal year 2022.",
            "Services revenue was $85.2 billion, growing 16% year-over-year.",
        ],
    }
