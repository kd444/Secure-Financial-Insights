"""Unit tests for the financial document chunker."""

import pytest

from src.document_processing.chunker import ChunkingConfig, FinancialDocumentChunker
from src.document_processing.sec_parser import ParsedFiling, ParsedSection, SECSection
from src.models.schemas import DocumentMetadata, FilingType


@pytest.fixture
def chunker():
    config = ChunkingConfig(max_tokens=100, overlap_tokens=20, min_chunk_tokens=10)
    return FinancialDocumentChunker(config=config)


@pytest.fixture
def sample_filing():
    return ParsedFiling(
        company_name="Apple Inc.",
        ticker="AAPL",
        filing_type="10-K",
        filing_date="2024-01-15",
        sections=[
            ParsedSection(
                section=SECSection.RISK_FACTORS,
                title="Item 1A - Risk Factors",
                content=(
                    "The company faces significant competition in the smartphone market. "
                    "Revenue may decline due to macroeconomic conditions. "
                    "Supply chain disruptions could impact manufacturing. "
                    "Regulatory changes in key markets present ongoing risks. "
                    "Currency fluctuations affect international revenue."
                ),
            ),
            ParsedSection(
                section=SECSection.MDA,
                title="Item 7 - Management Discussion and Analysis",
                content=(
                    "Revenue increased 8% year-over-year to $394.3 billion. "
                    "Services segment grew 16% to $85.2 billion. "
                    "Gross margin improved to 45.2% from 43.3%. "
                    "Operating expenses were $55.0 billion, up 5%."
                ),
            ),
        ],
        full_text="Full document text here.",
    )


class TestFinancialDocumentChunker:
    def test_chunk_filing_creates_chunks(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        assert len(chunks) > 0

    def test_chunks_have_metadata(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        for chunk in chunks:
            assert chunk.metadata.ticker == "AAPL"
            assert chunk.metadata.company_name == "Apple Inc."

    def test_chunks_have_section_context(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        # At least one chunk should contain section context prefix
        has_context = any("[Apple Inc." in c.content for c in chunks)
        assert has_context

    def test_chunks_have_sequential_indices(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunks_have_token_counts(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        for chunk in chunks:
            assert chunk.token_count > 0

    def test_chunk_text_basic(self, chunker):
        text = "This is a test sentence. " * 50
        metadata = DocumentMetadata(
            filing_type=FilingType.OTHER,
            company_name="Test",
            ticker="TST",
        )
        chunks = chunker.chunk_text(text, metadata)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata.ticker == "TST"

    def test_empty_filing_produces_no_chunks(self, chunker):
        empty_filing = ParsedFiling(
            company_name="Empty",
            ticker="EMP",
            filing_type="10-K",
            filing_date="",
            sections=[],
        )
        chunks = chunker.chunk_filing(empty_filing)
        assert len(chunks) == 0

    def test_document_ids_are_consistent_within_filing(self, chunker, sample_filing):
        chunks = chunker.chunk_filing(sample_filing)
        doc_ids = set(c.document_id for c in chunks)
        assert len(doc_ids) == 1  # all chunks share one document ID
