"""SEC EDGAR filing parser with section-aware extraction.

Parses 10-K, 10-Q, and 8-K filings into structured sections, preserving
financial table data and section metadata for downstream RAG citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from bs4 import BeautifulSoup

from src.core.logging import get_logger

logger = get_logger(__name__)


class SECSection(str, Enum):
    """Standard sections in SEC filings with their Item numbers."""

    # 10-K Sections
    BUSINESS = "Item 1 - Business"
    RISK_FACTORS = "Item 1A - Risk Factors"
    PROPERTIES = "Item 2 - Properties"
    LEGAL_PROCEEDINGS = "Item 3 - Legal Proceedings"
    MDA = "Item 7 - Management Discussion and Analysis"
    FINANCIAL_STATEMENTS = "Item 8 - Financial Statements"

    # 10-Q Sections
    FINANCIAL_STATEMENTS_Q = "Part I Item 1 - Financial Statements"
    MDA_Q = "Part I Item 2 - MD&A"
    RISK_FACTORS_Q = "Part II Item 1A - Risk Factors"

    # 8-K Sections
    ENTRY = "Item - Current Report Entry"

    UNKNOWN = "Unknown Section"


# Regex patterns for identifying SEC filing sections
SECTION_PATTERNS: dict[SECSection, list[re.Pattern[str]]] = {
    SECSection.RISK_FACTORS: [
        re.compile(r"item\s+1a[\.\s\-:]+risk\s+factors", re.IGNORECASE),
        re.compile(r"risk\s+factors", re.IGNORECASE),
    ],
    SECSection.MDA: [
        re.compile(
            r"item\s+7[\.\s\-:]+management.s?\s+discussion\s+and\s+analysis",
            re.IGNORECASE,
        ),
        re.compile(r"management.s?\s+discussion\s+and\s+analysis", re.IGNORECASE),
    ],
    SECSection.BUSINESS: [
        re.compile(r"item\s+1[\.\s\-:]+business(?!\s+combination)", re.IGNORECASE),
    ],
    SECSection.FINANCIAL_STATEMENTS: [
        re.compile(r"item\s+8[\.\s\-:]+financial\s+statements", re.IGNORECASE),
    ],
    SECSection.MDA_Q: [
        re.compile(
            r"part\s+i.*item\s+2[\.\s\-:]+management.s?\s+discussion",
            re.IGNORECASE,
        ),
    ],
    SECSection.RISK_FACTORS_Q: [
        re.compile(r"part\s+ii.*item\s+1a[\.\s\-:]+risk\s+factors", re.IGNORECASE),
    ],
}


@dataclass
class ParsedSection:
    section: SECSection
    title: str
    content: str
    tables: list[str] = field(default_factory=list)
    start_position: int = 0


@dataclass
class ParsedFiling:
    company_name: str
    ticker: str
    filing_type: str
    filing_date: str
    sections: list[ParsedSection] = field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


class SECFilingParser:
    """Parses SEC filing HTML/text into structured sections with table preservation."""

    def parse(self, raw_content: str, filing_metadata: dict[str, str]) -> ParsedFiling:
        """Parse raw SEC filing content into structured sections.

        Args:
            raw_content: Raw HTML or text content of the filing.
            filing_metadata: Dict with keys like company_name, ticker, filing_type, filing_date.

        Returns:
            ParsedFiling with extracted sections and metadata.
        """
        logger.info(
            "parsing_sec_filing",
            ticker=filing_metadata.get("ticker", ""),
            filing_type=filing_metadata.get("filing_type", ""),
        )

        # Strip HTML tags but preserve structure
        clean_text = self._clean_html(raw_content)

        # Extract tables before stripping them
        tables = self._extract_tables(raw_content)

        # Identify and extract sections
        sections = self._extract_sections(clean_text, tables)

        if not sections:
            # If no sections detected, treat entire text as one section
            sections = [
                ParsedSection(
                    section=SECSection.UNKNOWN,
                    title="Full Document",
                    content=clean_text,
                    tables=tables,
                )
            ]

        filing = ParsedFiling(
            company_name=filing_metadata.get("company_name", ""),
            ticker=filing_metadata.get("ticker", ""),
            filing_type=filing_metadata.get("filing_type", ""),
            filing_date=filing_metadata.get("filing_date", ""),
            sections=sections,
            full_text=clean_text,
            metadata=filing_metadata,
        )

        logger.info(
            "filing_parsed",
            sections_found=len(sections),
            total_length=len(clean_text),
        )
        return filing

    def _clean_html(self, content: str) -> str:
        """Remove HTML tags while preserving text structure."""
        if "<" in content and ">" in content:
            soup = BeautifulSoup(content, "lxml")
            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.decompose()
            text = soup.get_text(separator="\n")
        else:
            text = content

        # Normalize whitespace while preserving paragraph breaks
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
            elif lines and lines[-1] != "":
                lines.append("")

        return "\n".join(lines)

    def _extract_tables(self, content: str) -> list[str]:
        """Extract financial tables from HTML content."""
        tables: list[str] = []
        if "<table" not in content.lower():
            return tables

        soup = BeautifulSoup(content, "lxml")
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                tables.append("\n".join(rows))

        return tables

    def _extract_sections(
        self, text: str, tables: list[str]
    ) -> list[ParsedSection]:
        """Identify and extract named sections from filing text."""
        section_boundaries: list[tuple[int, SECSection, str]] = []

        for sec_type, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    section_boundaries.append((match.start(), sec_type, match.group()))
                    break  # take first match per section type

        if not section_boundaries:
            return []

        # Sort by position in document
        section_boundaries.sort(key=lambda x: x[0])

        sections: list[ParsedSection] = []
        for i, (start, sec_type, title) in enumerate(section_boundaries):
            # Section content runs from this header to the next header (or end of doc)
            end = (
                section_boundaries[i + 1][0]
                if i + 1 < len(section_boundaries)
                else len(text)
            )
            content = text[start:end].strip()

            # Attach relevant tables based on position heuristics
            section_tables = []
            if sec_type in (
                SECSection.FINANCIAL_STATEMENTS,
                SECSection.MDA,
                SECSection.MDA_Q,
            ):
                section_tables = tables  # financial sections get all tables

            sections.append(
                ParsedSection(
                    section=sec_type,
                    title=title,
                    content=content,
                    tables=section_tables,
                    start_position=start,
                )
            )

        return sections
