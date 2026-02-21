"""Query endpoints for the financial insights copilot.

Handles:
- Synchronous financial queries with RAG + evaluation
- Streaming queries for real-time token delivery
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_orchestrator
from src.models.schemas import QueryRequest, QueryResponse
from src.orchestration.workflow import QueryOrchestrator

router = APIRouter(prefix="/api/v1/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_financial_insights(
    request: QueryRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> QueryResponse:
    """Process a financial analysis query through the full RAG pipeline.

    The pipeline:
    1. Retrieves relevant document chunks via hybrid search
    2. Generates a response with citation injection
    3. Evaluates for hallucination, consistency, and confidence
    4. Applies PII redaction and content filtering
    5. Returns the response with quality scores and citations

    Query types:
    - risk_summary: Portfolio risk factor analysis
    - financial_analysis: Revenue, margins, cash flow analysis
    - market_impact: Event impact assessment
    - sec_filing_qa: Direct Q&A on SEC filings
    - investment_faq: General investment facts (no advice)
    - general: Open-ended financial queries
    """
    try:
        response = await orchestrator.execute(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stream")
async def stream_query(
    request: QueryRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """Stream a financial query response token-by-token.

    Note: Streaming mode skips evaluation (no quality scores).
    Use the synchronous endpoint for evaluated responses.
    """
    request.include_evaluation = False
    request.stream = True

    async def event_generator():
        try:
            # For streaming, we do retrieval first then stream generation
            response = await orchestrator.execute(request)
            # In a full implementation, this would stream tokens directly
            # For now, yield the complete response
            yield f"data: {response.response}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
