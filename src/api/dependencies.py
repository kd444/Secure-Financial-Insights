"""FastAPI dependency injection for shared services."""

from __future__ import annotations

from functools import lru_cache

from src.orchestration.workflow import QueryOrchestrator


@lru_cache(maxsize=1)
def _get_orchestrator_singleton() -> QueryOrchestrator:
    return QueryOrchestrator()


def get_orchestrator() -> QueryOrchestrator:
    """Dependency provider for the query orchestrator singleton."""
    return _get_orchestrator_singleton()
