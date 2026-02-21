"""SEC EDGAR filing downloader using the official EDGAR full-text search API.

Downloads filings from SEC EDGAR and prepares them for parsing.
Uses the sec-edgar-downloader library for reliable access.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sec_edgar_downloader import Downloader

from src.core.config import get_settings
from src.core.exceptions import DocumentProcessingError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Mapping from our filing types to SEC EDGAR form types
FILING_TYPE_MAP = {
    "10-K": "10-K",
    "10-Q": "10-Q",
    "8-K": "8-K",
}


class SECEdgarDownloader:
    """Downloads SEC filings from EDGAR for a given company ticker."""

    def __init__(self) -> None:
        settings = get_settings()
        self._user_agent = settings.sec_edgar_user_agent

    def download_filing(
        self,
        ticker: str,
        filing_type: str,
        num_filings: int = 1,
    ) -> list[dict[str, str]]:
        """Download SEC filings and return their content with metadata.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL').
            filing_type: Type of filing ('10-K', '10-Q', '8-K').
            num_filings: Number of most recent filings to download.

        Returns:
            List of dicts with 'content', 'filing_type', 'ticker', etc.

        Raises:
            DocumentProcessingError: If download or parsing fails.
        """
        form_type = FILING_TYPE_MAP.get(filing_type)
        if not form_type:
            raise DocumentProcessingError(
                f"Unsupported filing type: {filing_type}. "
                f"Supported: {list(FILING_TYPE_MAP.keys())}"
            )

        logger.info(
            "downloading_sec_filing",
            ticker=ticker,
            filing_type=form_type,
            num_filings=num_filings,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            dl = Downloader(company_name="FinancialInsights", email_address=self._user_agent.split()[-1], download_folder=tmpdir)

            try:
                dl.get(form_type, ticker, limit=num_filings)
            except Exception as e:
                raise DocumentProcessingError(
                    f"Failed to download {form_type} for {ticker}: {e}"
                ) from e

            # Find downloaded files
            filings = self._collect_filings(Path(tmpdir), ticker, filing_type)

        if not filings:
            raise DocumentProcessingError(
                f"No {filing_type} filings found for {ticker}"
            )

        logger.info(
            "filings_downloaded",
            ticker=ticker,
            count=len(filings),
        )
        return filings

    def _collect_filings(
        self, download_dir: Path, ticker: str, filing_type: str
    ) -> list[dict[str, str]]:
        """Collect and read downloaded filing files."""
        filings: list[dict[str, str]] = []

        # sec-edgar-downloader creates: download_dir/sec-edgar-filings/TICKER/TYPE/*/
        base = download_dir / "sec-edgar-filings" / ticker.upper()

        if not base.exists():
            return filings

        for filing_dir in sorted(base.rglob("*.txt")):
            try:
                content = filing_dir.read_text(encoding="utf-8", errors="replace")
                filings.append({
                    "content": content,
                    "filing_type": filing_type,
                    "ticker": ticker.upper(),
                    "company_name": ticker.upper(),
                    "filing_date": "",
                    "source_path": str(filing_dir),
                })
            except Exception as e:
                logger.warning(
                    "filing_read_error",
                    path=str(filing_dir),
                    error=str(e),
                )

        # Also check for htm/html files
        for ext in ("*.htm", "*.html"):
            for filing_file in sorted(base.rglob(ext)):
                try:
                    content = filing_file.read_text(encoding="utf-8", errors="replace")
                    filings.append({
                        "content": content,
                        "filing_type": filing_type,
                        "ticker": ticker.upper(),
                        "company_name": ticker.upper(),
                        "filing_date": "",
                        "source_path": str(filing_file),
                    })
                except Exception as e:
                    logger.warning(
                        "filing_read_error",
                        path=str(filing_file),
                        error=str(e),
                    )

        return filings
