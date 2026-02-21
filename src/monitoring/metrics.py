"""Prometheus metrics for LLM observability and application monitoring.

Defines domain-specific metrics for tracking:
- LLM performance (latency, tokens, errors, cost)
- RAG pipeline quality (retrieval relevance, chunk counts)
- Evaluation scores (hallucination, consistency, confidence)
- Guardrail events (PII detections, content filter triggers)
- Document processing throughput
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Summary

# === LLM Metrics ===

LLM_REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "LLM API request latency in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

LLM_TOKEN_USAGE = Counter(
    "llm_token_usage_total",
    "Total tokens consumed by LLM calls",
    ["type"],  # prompt, completion
)

LLM_REQUEST_ERRORS = Counter(
    "llm_request_errors_total",
    "Total LLM API request errors",
)

LLM_COST_USD = Counter(
    "llm_estimated_cost_usd_total",
    "Estimated cumulative LLM API cost in USD",
)

# === Embedding Metrics ===

EMBEDDING_LATENCY = Summary(
    "embedding_latency_seconds",
    "Embedding API call latency in seconds",
)

EMBEDDING_TOKENS = Counter(
    "embedding_tokens_total",
    "Total tokens used for embedding generation",
)

# === Retrieval Metrics ===

RETRIEVAL_LATENCY = Histogram(
    "retrieval_latency_seconds",
    "Time to retrieve and rank chunks",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

RETRIEVAL_CHUNKS_RETURNED = Histogram(
    "retrieval_chunks_returned",
    "Number of chunks returned per query",
    buckets=[1, 2, 4, 8, 16, 32],
)

RETRIEVAL_RELEVANCE_SCORE = Histogram(
    "retrieval_avg_relevance_score",
    "Average relevance score of retrieved chunks",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# === Evaluation Metrics ===

EVALUATION_SCORES = Histogram(
    "evaluation_score",
    "Evaluation pipeline scores",
    ["metric"],  # hallucination, consistency, confidence
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

EVALUATION_STATUS_COUNTER = Counter(
    "evaluation_status_total",
    "Count of evaluation verdicts",
    ["status"],  # passed, flagged, failed
)

EVALUATION_LATENCY = Histogram(
    "evaluation_latency_seconds",
    "Evaluation pipeline latency",
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0],
)

# === Guardrail Metrics ===

PII_DETECTIONS = Counter(
    "pii_detections_total",
    "Number of PII entities detected",
    ["entity_type"],
)

PII_REDACTIONS = Counter(
    "pii_redactions_total",
    "Number of PII redaction operations performed",
)

CONTENT_FILTER_VIOLATIONS = Counter(
    "content_filter_violations_total",
    "Content filter violation count",
    ["violation_type", "severity"],
)

# === Document Processing Metrics ===

DOCUMENTS_PROCESSED = Counter(
    "documents_processed_total",
    "Total documents ingested and processed",
    ["filing_type"],
)

CHUNKS_CREATED = Counter(
    "chunks_created_total",
    "Total document chunks created",
)

DOCUMENT_PROCESSING_LATENCY = Histogram(
    "document_processing_latency_seconds",
    "Document processing pipeline latency",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# === Query Metrics ===

QUERY_COUNT = Counter(
    "queries_total",
    "Total queries processed",
    ["query_type"],
)

QUERY_LATENCY = Histogram(
    "query_end_to_end_latency_seconds",
    "End-to-end query latency",
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# === System Health ===

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of currently processing requests",
)

VECTOR_STORE_SIZE = Gauge(
    "vector_store_total_chunks",
    "Total chunks in vector store",
)
