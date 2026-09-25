"""
Integration tests for FastAPI application health probes and middlewares.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.api.main import app


@pytest.mark.anyio
async def test_health_liveness_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time-Ms" in response.headers


@pytest.mark.anyio
async def test_readiness_probe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


@pytest.mark.anyio
async def test_api_v1_info_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["api_prefix"] == "/api/v1"
        assert data["name"] == "Wiring Diagram QC Assistant"
