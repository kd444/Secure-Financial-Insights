"""Intelligent document chunking with financial-domain awareness.

Uses a hybrid strategy combining:
- Semantic paragraph boundaries
- Section-aware splitting (preserves SEC section context)
- Token-count constraints for embedding models
- Overlap with sliding window for context continuity
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import tiktoken

from src.core.config import get_settings
from src.core.logging import get_logger
from src.document_processing.sec_parser import ParsedFiling, ParsedSection
from src.models.schemas import DocumentChunk, DocumentMetadata, FilingType

logger = get_logger(__name__)

# Financial-specific sentence boundaries (e.g., "ended Dec. 31, 2023")
FINANCIAL_BOUNDARY_PATTERN = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])|"  # standard sentence boundary
    r"(?<=\n\n)|"  # paragraph break
    r"(?<=\.\s{2})|"  # double-space after period
    r"(?<=:)\s*\n"  # colon followed by newline (often precedes lists)
)


@dataclass
class ChunkingConfig:
    max_tokens: int = 512
    overlap_tokens: int = 64
    min_chunk_tokens: int = 50
    preserve_tables: bool = True
    add_section_context: bool = True


class FinancialDocumentChunker:
    """Chunks financial documents with section-awareness and table preservation."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        settings = get_settings()
        self.config = config or ChunkingConfig(
            max_tokens=settings.chunk_size,
            overlap_tokens=settings.chunk_overlap,
        )
        self._encoder = tiktoken.encoding_for_model("gpt-4")

    def chunk_filing(self, filing: ParsedFiling) -> list[DocumentChunk]:
        """Chunk a parsed SEC filing into document chunks with metadata.

        Each chunk preserves:
        - Section context (which SEC section it belongs to)
        - Company metadata
        - Token count for embedding budgeting
        - Position index for ordering
        """
        all_chunks: list[DocumentChunk] = []
        document_id = str(uuid.uuid4())

        for section in filing.sections:
            section_chunks = self._chunk_section(section, filing, document_id)
            all_chunks.extend(section_chunks)

        # Reindex chunks sequentially
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i

        logger.info(
            "filing_chunked",
            document_id=document_id,
            total_chunks=len(all_chunks),
            ticker=filing.ticker,
        )
        return all_chunks

    def chunk_text(
        self, text: str, metadata: DocumentMetadata, document_id: str | None = None
    ) -> list[DocumentChunk]:
        """Chunk arbitrary text content (non-SEC documents)."""
        document_id = document_id or str(uuid.uuid4())
        sentences = self._split_into_sentences(text)
        chunks = self._merge_sentences_into_chunks(sentences)

        result: list[DocumentChunk] = []
        for i, chunk_text in enumerate(chunks):
            token_count = len(self._encoder.encode(chunk_text))
            result.append(
                DocumentChunk(
                    document_id=document_id,
                    content=chunk_text,
                    metadata=metadata,
                    chunk_index=i,
                    token_count=token_count,
                )
            )
        return result

    def _chunk_section(
        self, section: ParsedSection, filing: ParsedFiling, document_id: str
    ) -> list[DocumentChunk]:
        """Chunk a single section, prepending section context to each chunk."""
        metadata = DocumentMetadata(
            filing_type=FilingType(filing.filing_type)
            if filing.filing_type in [ft.value for ft in FilingType]
            else FilingType.OTHER,
            company_name=filing.company_name,
            ticker=filing.ticker,
            filing_date=filing.filing_date,
            section=section.section.value,
        )

        # Build section prefix for context injection
        section_prefix = ""
        if self.config.add_section_context:
            section_prefix = (
                f"[{filing.company_name} ({filing.ticker}) | "
                f"{filing.filing_type} | {section.section.value}]\n\n"
            )

        # Split section content into sentences
        sentences = self._split_into_sentences(section.content)

        # Merge sentences into token-bounded chunks
        chunks_text = self._merge_sentences_into_chunks(
            sentences, prefix_tokens=len(self._encoder.encode(section_prefix))
        )

        chunks: list[DocumentChunk] = []
        for i, chunk_text in enumerate(chunks_text):
            full_content = section_prefix + chunk_text if section_prefix else chunk_text
            token_count = len(self._encoder.encode(full_content))

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    content=full_content,
                    metadata=metadata,
                    chunk_index=i,
                    token_count=token_count,
                )
            )

        # Add table chunks if section has tables
        if self.config.preserve_tables and section.tables:
            for table in section.tables:
                table_content = section_prefix + f"[TABLE]\n{table}\n[/TABLE]"
                token_count = len(self._encoder.encode(table_content))
                if token_count > self.config.max_tokens:
                    # Split large tables
                    table_lines = table.split("\n")
                    sub_tables = self._split_table(table_lines, section_prefix)
                    chunks.extend(
                        DocumentChunk(
                            document_id=document_id,
                            content=st,
                            metadata=metadata,
                            chunk_index=len(chunks) + j,
                            token_count=len(self._encoder.encode(st)),
                        )
                        for j, st in enumerate(sub_tables)
                    )
                else:
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            content=table_content,
                            metadata=metadata,
                            chunk_index=len(chunks),
                            token_count=token_count,
                        )
                    )

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using financial-aware boundaries."""
        parts = FINANCIAL_BOUNDARY_PATTERN.split(text)
        return [s.strip() for s in parts if s and s.strip()]

    def _merge_sentences_into_chunks(
        self, sentences: list[str], prefix_tokens: int = 0
    ) -> list[str]:
        """Merge sentences into chunks respecting token limits with overlap."""
        if not sentences:
            return []

        max_tokens = self.config.max_tokens - prefix_tokens
        overlap_tokens = self.config.overlap_tokens
        chunks: list[str] = []
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = len(self._encoder.encode(sentence))

            if sentence_tokens > max_tokens:
                # Single sentence exceeds limit - force split by tokens
                if current_sentences:
                    chunks.append(" ".join(current_sentences))
                    current_sentences = []
                    current_tokens = 0
                # Token-level split for oversized sentences
                tokens = self._encoder.encode(sentence)
                for start in range(0, len(tokens), max_tokens - overlap_tokens):
                    chunk_tokens = tokens[start : start + max_tokens]
                    chunks.append(self._encoder.decode(chunk_tokens))
                continue

            if current_tokens + sentence_tokens > max_tokens:
                # Flush current chunk
                chunks.append(" ".join(current_sentences))

                # Calculate overlap: take sentences from the end
                overlap_sents: list[str] = []
                overlap_count = 0
                for s in reversed(current_sentences):
                    s_tokens = len(self._encoder.encode(s))
                    if overlap_count + s_tokens > overlap_tokens:
                        break
                    overlap_sents.insert(0, s)
                    overlap_count += s_tokens

                current_sentences = overlap_sents
                current_tokens = overlap_count

            current_sentences.append(sentence)
            current_tokens += sentence_tokens

        if current_sentences:
            text = " ".join(current_sentences)
            if len(self._encoder.encode(text)) >= self.config.min_chunk_tokens:
                chunks.append(text)
            elif chunks:
                # Merge small trailing chunk with previous
                chunks[-1] = chunks[-1] + " " + text

        return chunks

    def _split_table(self, table_lines: list[str], prefix: str) -> list[str]:
        """Split a large table into smaller chunks preserving the header row."""
        if not table_lines:
            return []

        header = table_lines[0]
        max_tokens = self.config.max_tokens

        sub_tables: list[str] = []
        current_lines = [header]
        current_tokens = len(self._encoder.encode(prefix + f"[TABLE]\n{header}"))

        for line in table_lines[1:]:
            line_tokens = len(self._encoder.encode(line))
            if current_tokens + line_tokens > max_tokens - 10:
                content = prefix + "[TABLE]\n" + "\n".join(current_lines) + "\n[/TABLE]"
                sub_tables.append(content)
                current_lines = [header]
                current_tokens = len(self._encoder.encode(prefix + f"[TABLE]\n{header}"))
            current_lines.append(line)
            current_tokens += line_tokens

        if len(current_lines) > 1:
            content = prefix + "[TABLE]\n" + "\n".join(current_lines) + "\n[/TABLE]"
            sub_tables.append(content)

        return sub_tables
