"""Domain-specific exceptions for the financial insights application."""

from __future__ import annotations


class FinancialInsightsError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        super().__init__(self.message)


class DocumentProcessingError(FinancialInsightsError):
    """Raised when document ingestion or parsing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="DOCUMENT_PROCESSING_ERROR")


class EmbeddingError(FinancialInsightsError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="EMBEDDING_ERROR")


class RetrievalError(FinancialInsightsError):
    """Raised when vector store retrieval fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="RETRIEVAL_ERROR")


class LLMError(FinancialInsightsError):
    """Raised when LLM inference fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="LLM_ERROR")


class HallucinationDetectedError(FinancialInsightsError):
    """Raised when the evaluation pipeline detects hallucinated output."""

    def __init__(self, message: str, confidence: float = 0.0) -> None:
        self.confidence = confidence
        super().__init__(message, error_code="HALLUCINATION_DETECTED")


class PIIDetectedError(FinancialInsightsError):
    """Raised when PII is detected in LLM output and cannot be redacted."""

    def __init__(self, message: str, entity_types: list[str] | None = None) -> None:
        self.entity_types = entity_types or []
        super().__init__(message, error_code="PII_DETECTED")


class RateLimitError(FinancialInsightsError):
    """Raised when API rate limits are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")


class GuardrailViolationError(FinancialInsightsError):
    """Raised when content violates guardrail policies."""

    def __init__(self, message: str, violation_type: str = "unknown") -> None:
        self.violation_type = violation_type
        super().__init__(message, error_code="GUARDRAIL_VIOLATION")
