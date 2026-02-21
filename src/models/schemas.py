"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# === Enums ===

class FilingType(str, Enum):
    TEN_K = "10-K"
    TEN_Q = "10-Q"
    EIGHT_K = "8-K"
    EARNINGS = "earnings"
    ANNUAL_REPORT = "annual_report"
    OTHER = "other"


class QueryType(str, Enum):
    RISK_SUMMARY = "risk_summary"
    FINANCIAL_ANALYSIS = "financial_analysis"
    MARKET_IMPACT = "market_impact"
    SEC_FILING_QA = "sec_filing_qa"
    INVESTMENT_FAQ = "investment_faq"
    GENERAL = "general"


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    FLAGGED = "flagged"
    FAILED = "failed"


# === Document Models ===

class DocumentMetadata(BaseModel):
    filing_type: FilingType = FilingType.OTHER
    company_name: str = ""
    ticker: str = ""
    filing_date: str = ""
    fiscal_year: str = ""
    fiscal_quarter: str = ""
    section: str = ""
    source_url: str = ""


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    content: str
    metadata: DocumentMetadata
    chunk_index: int
    token_count: int = 0
    embedding: list[float] | None = None


class DocumentUploadRequest(BaseModel):
    company_ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    filing_type: FilingType
    content: str | None = None  # raw text content
    file_url: str | None = None  # URL to fetch from


class DocumentUploadResponse(BaseModel):
    document_id: str
    chunks_created: int
    company: str
    filing_type: FilingType
    processing_time_ms: float
    status: str = "processed"


# === Query Models ===

class Citation(BaseModel):
    chunk_id: str
    source_document: str
    section: str
    relevance_score: float
    text_excerpt: str


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)
    query_type: QueryType = QueryType.GENERAL
    company_filter: str | None = None
    filing_type_filter: FilingType | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    include_evaluation: bool = True
    stream: bool = False


class EvaluationResult(BaseModel):
    hallucination_score: float = Field(ge=0.0, le=1.0, description="0=no hallucination, 1=full hallucination")
    factual_grounding_score: float = Field(ge=0.0, le=1.0)
    semantic_consistency_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    status: EvaluationStatus
    flags: list[str] = Field(default_factory=list)
    evaluation_reasoning: str = ""


class QueryResponse(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    response: str
    citations: list[Citation] = Field(default_factory=list)
    evaluation: EvaluationResult | None = None
    query_type: QueryType
    model_used: str = ""
    token_usage: TokenUsage | None = None
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    embedding_tokens: int = 0
    estimated_cost_usd: float = 0.0


# Fix forward reference
QueryResponse.model_rebuild()


# === Evaluation API Models ===

class EvaluationRequest(BaseModel):
    response_text: str
    source_chunks: list[str]
    query: str


class BatchEvaluationRequest(BaseModel):
    evaluations: list[EvaluationRequest]


class EvaluationMetrics(BaseModel):
    total_queries: int = 0
    avg_hallucination_score: float = 0.0
    avg_confidence_score: float = 0.0
    avg_consistency_score: float = 0.0
    pass_rate: float = 0.0
    flag_rate: float = 0.0
    fail_rate: float = 0.0
    avg_latency_ms: float = 0.0


# === Health & Monitoring ===

class HealthStatus(BaseModel):
    status: str = "healthy"
    version: str
    environment: str
    components: dict[str, ComponentHealth] | None = None


class ComponentHealth(BaseModel):
    status: str
    latency_ms: float = 0.0
    details: str = ""


# Fix forward reference
HealthStatus.model_rebuild()


# === SEC Filing Models ===

class SECFilingRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    filing_type: FilingType
    num_filings: int = Field(default=1, ge=1, le=10)


class SECFilingResponse(BaseModel):
    ticker: str
    filing_type: FilingType
    documents_processed: int
    total_chunks: int
    processing_time_ms: float
