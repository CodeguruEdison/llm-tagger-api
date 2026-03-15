"""Unit tests for health check endpoint."""
import pytest
from fastapi.testclient import TestClient

from tagging.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealthRouter:

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 with ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_returns_version(self, client):
        """Health endpoint includes version."""
        response = client.get("/health")
        assert "version" in response.json()
