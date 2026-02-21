"""LangGraph-based query orchestration workflow.

Defines a stateful graph that processes financial queries through:
1. Input validation & guardrails
2. Document retrieval (RAG)
3. LLM generation with prompt assembly
4. Output evaluation (hallucination, consistency, confidence)
5. Output guardrails (PII redaction, content filtering)
6. Response assembly with citations

The graph supports conditional edges for:
- Skipping evaluation when not requested
- Re-generation on evaluation failure
- Early termination on guardrail violations
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from src.core.config import get_settings
from src.core.logging import get_logger
from src.evaluation.evaluator import EvaluationPipeline
from src.guardrails.content_filter import ContentFilter
from src.guardrails.pii_redactor import PIIRedactor
from src.llm.client import LLMClient
from src.llm.prompts import build_rag_prompt
from src.models.schemas import (
    Citation,
    EvaluationResult,
    QueryRequest,
    QueryResponse,
    QueryType,
    TokenUsage,
)
from src.monitoring.metrics import (
    ACTIVE_REQUESTS,
    QUERY_COUNT,
    QUERY_LATENCY,
    PII_DETECTIONS,
    PII_REDACTIONS,
    CONTENT_FILTER_VIOLATIONS,
)
from src.rag.embeddings import EmbeddingService
from src.rag.retriever import HybridRetriever
from src.rag.vector_store import create_vector_store

logger = get_logger(__name__)

MAX_REGENERATION_ATTEMPTS = 2


@dataclass
class WorkflowState:
    """Mutable state passed through the workflow graph."""

    # Input
    query: str = ""
    query_type: QueryType = QueryType.GENERAL
    company_filter: str | None = None
    filing_type_filter: str | None = None
    top_k: int = 5
    include_evaluation: bool = True

    # Retrieval
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    chunk_texts: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)

    # Generation
    messages: list[dict[str, str]] = field(default_factory=list)
    response_text: str = ""
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    model_used: str = ""

    # Evaluation
    evaluation: EvaluationResult | None = None
    generation_attempts: int = 0

    # Guardrails
    pii_entities_found: int = 0
    content_filter_passed: bool = True
    warnings: list[str] = field(default_factory=list)

    # Metadata
    start_time: float = 0.0
    error: str | None = None


class QueryOrchestrator:
    """Builds and executes the LangGraph workflow for financial queries."""

    def __init__(self) -> None:
        settings = get_settings()

        # Initialize components
        self._embedding_service = EmbeddingService()
        self._vector_store = create_vector_store()
        self._retriever = HybridRetriever(self._embedding_service, self._vector_store)
        self._llm_client = LLMClient()
        self._evaluation = EvaluationPipeline(self._llm_client, self._embedding_service)
        self._pii_redactor = PIIRedactor()
        self._content_filter = ContentFilter()

        # Build the workflow graph
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Construct the LangGraph state machine."""
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("guardrails", self._guardrails_node)
        workflow.add_node("assemble", self._assemble_node)

        # Define edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_conditional_edges(
            "generate",
            self._should_evaluate,
            {
                "evaluate": "evaluate",
                "skip_eval": "guardrails",
            },
        )
        workflow.add_conditional_edges(
            "evaluate",
            self._should_regenerate,
            {
                "regenerate": "generate",
                "continue": "guardrails",
            },
        )
        workflow.add_edge("guardrails", "assemble")
        workflow.add_edge("assemble", END)

        return workflow.compile()

    async def execute(self, request: QueryRequest) -> QueryResponse:
        """Execute the full query workflow.

        Args:
            request: The incoming query request.

        Returns:
            QueryResponse with answer, citations, evaluation, and metadata.
        """
        ACTIVE_REQUESTS.inc()
        QUERY_COUNT.labels(query_type=request.query_type.value).inc()

        state = WorkflowState(
            query=request.query,
            query_type=request.query_type,
            company_filter=request.company_filter,
            filing_type_filter=request.filing_type_filter.value
            if request.filing_type_filter
            else None,
            top_k=request.top_k,
            include_evaluation=request.include_evaluation,
            start_time=time.perf_counter(),
        )

        try:
            # Execute the graph
            final_state = await self._graph.ainvoke(state)

            elapsed_ms = (time.perf_counter() - state.start_time) * 1000
            QUERY_LATENCY.observe(elapsed_ms / 1000)

            response = QueryResponse(
                query=request.query,
                response=final_state.response_text,
                citations=final_state.citations,
                evaluation=final_state.evaluation,
                query_type=request.query_type,
                model_used=final_state.model_used,
                token_usage=final_state.token_usage,
                latency_ms=round(elapsed_ms, 2),
            )

            return response

        finally:
            ACTIVE_REQUESTS.dec()

    # === Workflow Nodes ===

    async def _retrieve_node(self, state: WorkflowState) -> WorkflowState:
        """Retrieve relevant document chunks."""
        logger.info("workflow_retrieve", query=state.query[:100])

        metadata_filter: dict[str, Any] = {}
        if state.company_filter:
            metadata_filter["ticker"] = state.company_filter.upper()
        if state.filing_type_filter:
            metadata_filter["filing_type"] = state.filing_type_filter

        chunks, citations = await self._retriever.retrieve(
            query=state.query,
            top_k=state.top_k,
            metadata_filter=metadata_filter if metadata_filter else None,
        )

        state.retrieved_chunks = chunks
        state.chunk_texts = [c["content"] for c in chunks]
        state.citations = citations
        return state

    async def _generate_node(self, state: WorkflowState) -> WorkflowState:
        """Generate LLM response from retrieved context."""
        state.generation_attempts += 1
        logger.info(
            "workflow_generate",
            attempt=state.generation_attempts,
        )

        # Build prompt with context
        messages = build_rag_prompt(
            query=state.query,
            context_chunks=state.chunk_texts,
            query_type=state.query_type,
        )
        state.messages = messages

        # Generate
        response_text, usage = await self._llm_client.generate(messages=messages)

        state.response_text = response_text
        state.token_usage = usage
        state.model_used = self._llm_client.model_name
        return state

    async def _evaluate_node(self, state: WorkflowState) -> WorkflowState:
        """Run evaluation pipeline on the response."""
        logger.info("workflow_evaluate")

        evaluation = await self._evaluation.evaluate(
            response_text=state.response_text,
            source_chunks=state.chunk_texts,
            query=state.query,
            citations=state.citations,
            messages=state.messages,
            run_consistency=(state.generation_attempts == 1),
        )

        state.evaluation = evaluation
        return state

    async def _guardrails_node(self, state: WorkflowState) -> WorkflowState:
        """Apply PII redaction and content filtering."""
        logger.info("workflow_guardrails")

        # PII redaction
        pii_result = self._pii_redactor.redact(state.response_text)
        if pii_result.was_redacted:
            state.response_text = pii_result.redacted_text
            state.pii_entities_found = pii_result.entity_count
            PII_REDACTIONS.inc()
            for entity in pii_result.entities_found:
                PII_DETECTIONS.labels(entity_type=entity.entity_type.value).inc()

        # Content filtering
        filter_result = self._content_filter.filter(state.response_text)
        state.content_filter_passed = filter_result.passed
        state.response_text = filter_result.filtered_text
        state.warnings.extend(filter_result.warnings)

        for violation in filter_result.violations:
            CONTENT_FILTER_VIOLATIONS.labels(
                violation_type=violation.violation_type.value,
                severity=violation.severity,
            ).inc()

        return state

    async def _assemble_node(self, state: WorkflowState) -> WorkflowState:
        """Final assembly - no-op, state is already complete."""
        logger.info(
            "workflow_complete",
            latency_ms=round((time.perf_counter() - state.start_time) * 1000, 2),
            evaluation_status=state.evaluation.status.value if state.evaluation else "skipped",
        )
        return state

    # === Conditional Edges ===

    @staticmethod
    def _should_evaluate(state: WorkflowState) -> Literal["evaluate", "skip_eval"]:
        if state.include_evaluation:
            return "evaluate"
        return "skip_eval"

    @staticmethod
    def _should_regenerate(state: WorkflowState) -> Literal["regenerate", "continue"]:
        if (
            state.evaluation
            and state.evaluation.hallucination_score > 0.8
            and state.generation_attempts < MAX_REGENERATION_ATTEMPTS
        ):
            logger.warning(
                "regenerating_due_to_hallucination",
                score=state.evaluation.hallucination_score,
                attempt=state.generation_attempts,
            )
            return "regenerate"
        return "continue"

    @property
    def embedding_service(self) -> EmbeddingService:
        return self._embedding_service

    @property
    def vector_store(self) -> Any:
        return self._vector_store
