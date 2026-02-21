"""Integration tests for the FastAPI application endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.integration
class TestHealthEndpoints:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "environment" in data

    async def test_readiness_probe(self, client):
        response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    async def test_liveness_probe(self, client):
        response = await client.get("/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


@pytest.mark.integration
class TestQueryEndpoints:
    async def test_query_validation_short_query(self, client):
        response = await client.post(
            "/api/v1/query/",
            json={"query": "Hi"},
        )
        assert response.status_code == 422  # validation error

    async def test_query_validation_valid_structure(self, client):
        response = await client.post(
            "/api/v1/query/",
            json={
                "query": "What are Apple's main risk factors?",
                "query_type": "risk_summary",
                "company_filter": "AAPL",
                "top_k": 5,
                "include_evaluation": False,
            },
        )
        # May fail with 500 if no OpenAI key, but should not be 422
        assert response.status_code in (200, 500)


@pytest.mark.integration
class TestDocumentEndpoints:
    async def test_ingest_missing_content(self, client):
        response = await client.post(
            "/api/v1/documents/ingest",
            json={
                "company_ticker": "AAPL",
                "filing_type": "10-K",
            },
        )
        assert response.status_code == 400

    async def test_upload_wrong_filetype(self, client):
        import io
        files = {"file": ("test.exe", io.BytesIO(b"content"), "application/octet-stream")}
        response = await client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400


@pytest.mark.integration
class TestEvaluationEndpoints:
    async def test_evaluation_metrics(self, client):
        response = await client.get("/api/v1/evaluation/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "avg_hallucination_score" in data
