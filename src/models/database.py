"""SQLAlchemy models for persistent storage of queries, evaluations, and audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class QueryLog(Base):
    """Stores every query and response for audit and analytics."""

    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=False)
    response_text = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=False)
    company_filter = Column(String(20), nullable=True)

    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)

    # Evaluation scores
    hallucination_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)
    factual_grounding_score = Column(Float, nullable=True)
    evaluation_status = Column(String(20), nullable=True)

    # Metadata
    latency_ms = Column(Float, default=0.0)
    citations_count = Column(Integer, default=0)
    citations_json = Column(JSONB, nullable=True)
    pii_detected = Column(Boolean, default=False)
    pii_entities_redacted = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentRecord(Base):
    """Tracks ingested documents and their processing status."""

    __tablename__ = "document_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(200), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    filing_type = Column(String(50), nullable=False)
    filing_date = Column(String(20), nullable=True)
    source_url = Column(Text, nullable=True)

    chunks_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    processing_time_ms = Column(Float, default=0.0)
    status = Column(String(20), default="processed")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EvaluationLog(Base):
    """Stores evaluation results for trend analysis and monitoring."""

    __tablename__ = "evaluation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_log_id = Column(UUID(as_uuid=True), nullable=True)

    hallucination_score = Column(Float, nullable=False)
    factual_grounding_score = Column(Float, nullable=False)
    semantic_consistency_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    flags = Column(JSONB, nullable=True)
    reasoning = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class GuardrailEvent(Base):
    """Audit log for guardrail triggers (PII detection, content filtering)."""

    __tablename__ = "guardrail_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # pii_detection, content_filter, etc.
    query_log_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, nullable=True)
    action_taken = Column(String(50), nullable=False)  # redacted, blocked, flagged
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
