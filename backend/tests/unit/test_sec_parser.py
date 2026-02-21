"""Unit tests for the SEC filing parser."""

import pytest

from src.document_processing.sec_parser import SECFilingParser, SECSection


@pytest.fixture
def parser():
    return SECFilingParser()


@pytest.fixture
def sample_10k_text():
    return """
    UNITED STATES SECURITIES AND EXCHANGE COMMISSION
    Washington, D.C. 20549

    FORM 10-K

    Item 1 - Business

    Apple Inc. designs, manufactures, and markets smartphones, personal computers,
    tablets, wearables, and accessories. The Company also sells various related
    services including advertising, AppleCare, cloud, digital content, payment
    and other services.

    Item 1A - Risk Factors

    The following discussion of risk factors contains forward-looking statements.
    The Company's operations and financial results are subject to risks and
    uncertainties. Revenue concentration in a limited number of products presents
    significant business risk. Economic conditions globally could materially
    adversely affect the Company's business and results.

    Item 7 - Management's Discussion and Analysis of Financial Condition

    Revenue increased by 8% or $29.0 billion during 2023 compared to 2022.
    Products revenue was $298.1 billion during 2023. Services revenue was
    $85.2 billion during 2023 compared to $78.1 billion during 2022.
    Gross margin percentage increased from 43.3% to 45.2%.

    Item 8 - Financial Statements and Supplementary Data

    CONSOLIDATED STATEMENTS OF OPERATIONS
    Net sales: $394,328 million
    Cost of sales: $214,137 million
    Gross margin: $180,191 million
    """


class TestSECFilingParser:
    def test_parse_extracts_sections(self, parser, sample_10k_text):
        filing = parser.parse(
            raw_content=sample_10k_text,
            filing_metadata={
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "filing_type": "10-K",
                "filing_date": "2024-01-15",
            },
        )
        assert len(filing.sections) >= 3
        section_types = [s.section for s in filing.sections]
        assert SECSection.RISK_FACTORS in section_types
        assert SECSection.MDA in section_types

    def test_parse_preserves_metadata(self, parser, sample_10k_text):
        filing = parser.parse(
            raw_content=sample_10k_text,
            filing_metadata={
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "filing_type": "10-K",
                "filing_date": "2024-01-15",
            },
        )
        assert filing.company_name == "Apple Inc."
        assert filing.ticker == "AAPL"
        assert filing.filing_type == "10-K"

    def test_parse_html_content(self, parser):
        html = """
        <html><body>
        <h2>Item 1A - Risk Factors</h2>
        <p>The company faces risks related to market competition.</p>
        <h2>Item 7 - Management's Discussion and Analysis</h2>
        <p>Revenue was $100 million, up 10% year-over-year.</p>
        </body></html>
        """
        filing = parser.parse(
            raw_content=html,
            filing_metadata={"company_name": "Test", "ticker": "TST", "filing_type": "10-K", "filing_date": ""},
        )
        assert len(filing.sections) >= 2

    def test_parse_plain_text_no_sections(self, parser):
        plain = "This is a plain text document with no SEC section headers."
        filing = parser.parse(
            raw_content=plain,
            filing_metadata={"company_name": "Test", "ticker": "TST", "filing_type": "other", "filing_date": ""},
        )
        # Should return one UNKNOWN section
        assert len(filing.sections) == 1
        assert filing.sections[0].section == SECSection.UNKNOWN

    def test_clean_html_removes_scripts(self, parser):
        html_with_script = "<html><script>alert('test')</script><body>Content here</body></html>"
        text = parser._clean_html(html_with_script)
        assert "alert" not in text
        assert "Content here" in text

    def test_extract_tables(self, parser):
        html_with_table = """
        <html><body>
        <table>
        <tr><th>Revenue</th><th>2023</th><th>2022</th></tr>
        <tr><td>Products</td><td>$298.1B</td><td>$275.3B</td></tr>
        <tr><td>Services</td><td>$85.2B</td><td>$78.1B</td></tr>
        </table>
        </body></html>
        """
        tables = parser._extract_tables(html_with_table)
        assert len(tables) == 1
        assert "Revenue" in tables[0]
        assert "$298.1B" in tables[0]
