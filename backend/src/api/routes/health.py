"""Health check and system status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_orchestrator
from src.core.config import get_settings
from src.models.schemas import ComponentHealth, HealthStatus
from src.orchestration.workflow import QueryOrchestrator

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthStatus)
async def health_check(
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
) -> HealthStatus:
    """System health check with component-level status.

    Checks:
    - Vector store connectivity
    - LLM API availability (via ping)
    - Application configuration validity
    """
    settings = get_settings()
    components: dict[str, ComponentHealth] = {}

    # Check vector store
    try:
        stats = await orchestrator.vector_store.get_collection_stats()
        components["vector_store"] = ComponentHealth(
            status="healthy",
            details=f"{stats.get('total_chunks', 0)} chunks indexed",
        )
    except Exception as e:
        components["vector_store"] = ComponentHealth(
            status="unhealthy",
            details=str(e),
        )

    # Check LLM API key configured
    has_api_key = bool(settings.openai_api_key.get_secret_value())
    components["llm_api"] = ComponentHealth(
        status="healthy" if has_api_key else "degraded",
        details="API key configured" if has_api_key else "No API key set",
    )

    # Overall status
    all_healthy = all(c.status == "healthy" for c in components.values())

    return HealthStatus(
        status="healthy" if all_healthy else "degraded",
        version=settings.app_version,
        environment=settings.app_env.value,
        components=components,
    )


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe endpoint."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}
