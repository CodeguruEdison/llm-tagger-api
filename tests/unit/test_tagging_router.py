"""Unit tests for tagging router."""
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from tagging.api.app import create_app
from tagging.api.dependencies import get_orchestrator
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult


def make_tag_result() -> TagResult:
    return TagResult(
        tag=Tag(
            id="tag-1",
            category_id="cat-1",
            name="Parts Delay",
            slug="parts-delay",
            description="Waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        ),
        confidence=1.0,
        source=TagSource.RULES,
        reasoning="matched rule: Parts Delay Detection",
    )


class TestTaggingRouter:

    def _client_with_mock_orchestrator(self, results):
        """Create test client with mocked orchestrator."""
        app = create_app()
        mock_orchestrator = MagicMock()
        mock_orchestrator.tag_note = AsyncMock(return_value=results)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        return TestClient(app)

    def test_tag_note_returns_results(self):
        """POST /tag returns tag results."""
        client = self._client_with_mock_orchestrator([make_tag_result()])
        response = client.post("/tag", json={
            "note_id": "note-1",
            "ro_id": "ro-1",
            "shop_id": "shop-1",
            "text": "waiting on parts from LKQ",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["note_id"] == "note-1"
        assert data["total"] == 1
        assert data["results"][0]["tag"]["slug"] == "parts-delay"
        assert data["results"][0]["confidence"] == 1.0
        assert data["results"][0]["source"] == "RULES"

    def test_tag_note_empty_results(self):
        """POST /tag returns empty results when no tags match."""
        client = self._client_with_mock_orchestrator([])
        response = client.post("/tag", json={
            "note_id": "note-1",
            "ro_id": "ro-1",
            "shop_id": "shop-1",
            "text": "vehicle is ready for pickup",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_tag_note_empty_text_returns_422(self):
        """POST /tag with empty text returns 422 validation error."""
        client = self._client_with_mock_orchestrator([])
        response = client.post("/tag", json={
            "note_id": "note-1",
            "ro_id": "ro-1",
            "shop_id": "shop-1",
            "text": "   ",
        })
        assert response.status_code == 422
