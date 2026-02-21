"""Script to ingest sample SEC filings for demonstration.

Usage:
    python -m scripts.ingest_sample --ticker AAPL --filing-type 10-K
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from src.core.config import get_settings
from src.core.logging import setup_logging, get_logger
from src.document_processing.chunker import FinancialDocumentChunker
from src.document_processing.sec_downloader import SECEdgarDownloader
from src.document_processing.sec_parser import SECFilingParser
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import create_vector_store

logger = get_logger(__name__)


async def ingest(ticker: str, filing_type: str, num_filings: int = 1) -> None:
    setup_logging()
    settings = get_settings()

    logger.info("starting_ingestion", ticker=ticker, filing_type=filing_type)
    start = time.perf_counter()

    # Download
    downloader = SECEdgarDownloader()
    filings = downloader.download_filing(ticker, filing_type, num_filings)
    logger.info("filings_downloaded", count=len(filings))

    # Parse and chunk
    parser = SECFilingParser()
    chunker = FinancialDocumentChunker()
    embedding_service = EmbeddingService()
    vector_store = create_vector_store()

    total_chunks = 0
    for filing_data in filings:
        parsed = parser.parse(filing_data["content"], filing_data)
        chunks = chunker.chunk_filing(parsed)

        if chunks:
            texts = [c.content for c in chunks]
            embeddings = await embedding_service.embed_texts(texts)
            await vector_store.add_chunks(chunks, embeddings)
            total_chunks += len(chunks)
            logger.info("filing_ingested", chunks=len(chunks))

    elapsed = time.perf_counter() - start
    logger.info(
        "ingestion_complete",
        total_chunks=total_chunks,
        elapsed_seconds=round(elapsed, 2),
    )

    stats = await vector_store.get_collection_stats()
    logger.info("vector_store_stats", **stats)


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Ingest SEC filings")
    arg_parser.add_argument("--ticker", required=True, help="Stock ticker (e.g., AAPL)")
    arg_parser.add_argument("--filing-type", default="10-K", help="Filing type (10-K, 10-Q, 8-K)")
    arg_parser.add_argument("--num-filings", type=int, default=1, help="Number of filings")
    args = arg_parser.parse_args()

    asyncio.run(ingest(args.ticker, args.filing_type, args.num_filings))


if __name__ == "__main__":
    main()
