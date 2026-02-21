"""Evaluation and quality monitoring endpoints.

Provides APIs for:
- On-demand evaluation of LLM outputs
- Evaluation metrics aggregation
- Quality trend monitoring
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_orchestrator
from src.models.schemas import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationMetrics,
)
from src.orchestration.workflow import QueryOrchestrator

router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation"])


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_response(
    request: EvaluationRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> EvaluationResult:
    """Evaluate an LLM response against source documents.

    Runs the full evaluation pipeline:
    - Hallucination detection (LLM-as-judge + entity overlap + semantic similarity)
    - Self-consistency scoring
    - Confidence scoring (citation density, specificity, hedging)

    Use this to evaluate responses from external LLM systems or
    to re-evaluate previously generated responses.
    """
    try:
        from src.evaluation.evaluator import EvaluationPipeline
        from src.llm.client import LLMClient
        from src.rag.embeddings import EmbeddingService

        pipeline = EvaluationPipeline(
            llm_client=LLMClient(),
            embedding_service=EmbeddingService(),
        )

        result = await pipeline.evaluate(
            response_text=request.response_text,
            source_chunks=request.source_chunks,
            query=request.query,
            citations=[],
            run_consistency=True,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics", response_model=EvaluationMetrics)
async def get_evaluation_metrics() -> EvaluationMetrics:
    """Get aggregated evaluation metrics.

    Returns average scores across all evaluated queries,
    useful for monitoring LLM quality trends over time.
    """
    # In production, this would query the database for aggregated metrics.
    # For now, return placeholder structure showing the API contract.
    return EvaluationMetrics(
        total_queries=0,
        avg_hallucination_score=0.0,
        avg_confidence_score=0.0,
        avg_consistency_score=0.0,
        pass_rate=0.0,
        flag_rate=0.0,
        fail_rate=0.0,
        avg_latency_ms=0.0,
    )
