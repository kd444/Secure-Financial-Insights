"""FastAPI application entry point.

Configures:
- CORS middleware
- Prometheus metrics instrumentation
- API route registration
- Structured logging
- Lifespan events (startup/shutdown)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.routes import documents, evaluation, health, query
from src.core.config import get_settings
from src.core.exceptions import FinancialInsightsError
from src.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events for startup and shutdown."""
    setup_logging()
    settings = get_settings()
    logger.info(
        "application_starting",
        environment=settings.app_env.value,
        version=settings.app_version,
    )
    yield
    logger.info("application_shutting_down")


def create_app() -> FastAPI:
    """Application factory for the Financial Insights Copilot."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise GenAI copilot for financial document analysis. "
            "Provides RAG-based Q&A over SEC filings with hallucination detection, "
            "LLM quality monitoring, and financial compliance guardrails."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics
    if settings.prometheus_enabled:
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/ready", "/live", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")

    # Register routes
    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(documents.router)
    app.include_router(evaluation.router)

    # Global exception handler
    @app.exception_handler(FinancialInsightsError)
    async def financial_insights_error_handler(
        request: Request, exc: FinancialInsightsError
    ) -> JSONResponse:
        logger.error(
            "application_error",
            error_code=exc.error_code,
            message=exc.message,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )
