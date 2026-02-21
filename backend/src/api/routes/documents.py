"""Document ingestion endpoints for SEC filings and financial documents."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from src.api.dependencies import get_orchestrator
from src.core.exceptions import DocumentProcessingError
from src.document_processing.chunker import FinancialDocumentChunker
from src.document_processing.sec_downloader import SECEdgarDownloader
from src.document_processing.sec_parser import SECFilingParser
from src.models.schemas import (
    DocumentMetadata,
    DocumentUploadRequest,
    DocumentUploadResponse,
    SECFilingRequest,
    SECFilingResponse,
)
from src.monitoring.metrics import (
    CHUNKS_CREATED,
    DOCUMENTS_PROCESSED,
    DOCUMENT_PROCESSING_LATENCY,
)
from src.orchestration.workflow import QueryOrchestrator

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/ingest", response_model=DocumentUploadResponse)
async def ingest_document(
    request: DocumentUploadRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> DocumentUploadResponse:
    """Ingest a financial document (raw text or URL).

    Processes the document through:
    1. Parsing and section extraction
    2. Financial-aware chunking with metadata
    3. Embedding generation
    4. Vector store indexing
    """
    start = time.perf_counter()

    if not request.content and not request.file_url:
        raise HTTPException(
            status_code=400,
            detail="Either 'content' or 'file_url' must be provided",
        )

    try:
        content = request.content or ""

        # Parse
        parser = SECFilingParser()
        filing = parser.parse(
            raw_content=content,
            filing_metadata={
                "company_name": request.company_ticker,
                "ticker": request.company_ticker,
                "filing_type": request.filing_type.value,
                "filing_date": "",
            },
        )

        # Chunk
        chunker = FinancialDocumentChunker()
        chunks = chunker.chunk_filing(filing)

        # Embed and store
        chunk_texts = [c.content for c in chunks]
        embeddings = await orchestrator.embedding_service.embed_texts(chunk_texts)
        stored = await orchestrator.vector_store.add_chunks(chunks, embeddings)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Track metrics
        DOCUMENTS_PROCESSED.labels(filing_type=request.filing_type.value).inc()
        CHUNKS_CREATED.inc(len(chunks))
        DOCUMENT_PROCESSING_LATENCY.observe(elapsed_ms / 1000)

        return DocumentUploadResponse(
            document_id=chunks[0].document_id if chunks else "",
            chunks_created=stored,
            company=request.company_ticker,
            filing_type=request.filing_type,
            processing_time_ms=round(elapsed_ms, 2),
        )

    except DocumentProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ingest/sec", response_model=SECFilingResponse)
async def ingest_sec_filing(
    request: SECFilingRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> SECFilingResponse:
    """Download and ingest SEC filings directly from EDGAR.

    Fetches the specified filing type for a company ticker from
    SEC EDGAR, parses it into sections, chunks it, and indexes
    it in the vector store.
    """
    start = time.perf_counter()

    try:
        # Download from SEC EDGAR
        downloader = SECEdgarDownloader()
        filings = downloader.download_filing(
            ticker=request.ticker,
            filing_type=request.filing_type.value,
            num_filings=request.num_filings,
        )

        parser = SECFilingParser()
        chunker = FinancialDocumentChunker()
        total_chunks = 0

        for filing_data in filings:
            # Parse
            parsed = parser.parse(
                raw_content=filing_data["content"],
                filing_metadata=filing_data,
            )

            # Chunk
            chunks = chunker.chunk_filing(parsed)

            # Embed and store
            if chunks:
                texts = [c.content for c in chunks]
                embeddings = await orchestrator.embedding_service.embed_texts(texts)
                await orchestrator.vector_store.add_chunks(chunks, embeddings)
                total_chunks += len(chunks)

        elapsed_ms = (time.perf_counter() - start) * 1000

        DOCUMENTS_PROCESSED.labels(filing_type=request.filing_type.value).inc(len(filings))
        CHUNKS_CREATED.inc(total_chunks)
        DOCUMENT_PROCESSING_LATENCY.observe(elapsed_ms / 1000)

        return SECFilingResponse(
            ticker=request.ticker,
            filing_type=request.filing_type,
            documents_processed=len(filings),
            total_chunks=total_chunks,
            processing_time_ms=round(elapsed_ms, 2),
        )

    except DocumentProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> DocumentUploadResponse:
    """Upload a financial document file (PDF, TXT, HTML)."""
    start = time.perf_counter()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_extensions = {".txt", ".html", ".htm", ".pdf"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_extensions}",
        )

    try:
        content = await file.read()
        text_content = content.decode("utf-8", errors="replace")

        parser = SECFilingParser()
        filing = parser.parse(
            raw_content=text_content,
            filing_metadata={
                "company_name": file.filename,
                "ticker": "",
                "filing_type": "other",
                "filing_date": "",
            },
        )

        chunker = FinancialDocumentChunker()
        chunks = chunker.chunk_filing(filing)

        if chunks:
            texts = [c.content for c in chunks]
            embeddings = await orchestrator.embedding_service.embed_texts(texts)
            await orchestrator.vector_store.add_chunks(chunks, embeddings)

        elapsed_ms = (time.perf_counter() - start) * 1000

        from src.models.schemas import FilingType
        return DocumentUploadResponse(
            document_id=chunks[0].document_id if chunks else "",
            chunks_created=len(chunks),
            company=file.filename,
            filing_type=FilingType.OTHER,
            processing_time_ms=round(elapsed_ms, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
