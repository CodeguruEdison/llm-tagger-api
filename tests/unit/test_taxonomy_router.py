"""Unit tests for taxonomy router."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from tagging.api.app import create_app
from tagging.api.dependencies import get_repository
from tagging.domain.tag import Tag
from tagging.domain.tag_category import TagCategory


def make_category() -> TagCategory:
    return TagCategory(
        id="cat-1",
        name="Parts",
        slug="parts",
        description="Parts issues",
        is_active=True,
        sort_order=1,
    )


def make_tag() -> Tag:
    return Tag(
        id="tag-1",
        category_id="cat-1",
        name="Parts Delay",
        slug="parts-delay",
        description="Waiting on parts",
        color="#FF6B6B",
        icon="clock",
        priority=1,
        is_active=True,
    )


def make_client(categories=None, tags=None):
    app = create_app()
    mock_repo = MagicMock()
    mock_repo.get_all_categories = AsyncMock(return_value=categories or [])
    mock_repo.get_all_active_tags = AsyncMock(return_value=tags or [])
    app.dependency_overrides[get_repository] = lambda: mock_repo
    return TestClient(app)


class TestTaxonomyRouter:
    def test_get_taxonomy(self):
        """GET /taxonomy returns categories and tags."""
        client = make_client(
            categories=[make_category()],
            tags=[make_tag()],
        )
        response = client.get("/taxonomy")
        assert response.status_code == 200
        data = response.json()
        assert data["total_categories"] == 1
        assert data["total_tags"] == 1
        assert data["categories"][0]["slug"] == "parts"
        assert data["tags"][0]["slug"] == "parts-delay"

    def test_get_categories(self):
        """GET /taxonomy/categories returns category list."""
        client = make_client(categories=[make_category()])
        response = client.get("/taxonomy/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Parts"

    def test_get_tags(self):
        """GET /taxonomy/tags returns tag list."""
        client = make_client(tags=[make_tag()])
        response = client.get("/taxonomy/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "parts-delay"

    def test_empty_taxonomy(self):
        """GET /taxonomy with no data returns empty lists."""
        client = make_client()
        response = client.get("/taxonomy")
        assert response.status_code == 200
        data = response.json()
        assert data["total_categories"] == 0
        assert data["total_tags"] == 0

    def test_create_category(self):
        """POST /taxonomy/categories creates and returns category."""
        app = create_app()
        mock_repo = MagicMock()
        mock_repo.create_category = AsyncMock(side_effect=lambda c: c)
        app.dependency_overrides[get_repository] = lambda: mock_repo
        client = TestClient(app)
        response = client.post(
            "/taxonomy/categories",
            json={
                "name": "Parts",
                "slug": "parts",
                "description": "Parts related issues",
                "is_active": True,
                "sort_order": 1,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Parts"
        assert data["slug"] == "parts"

    def test_create_tag(self):
        """POST /taxonomy/tags creates and returns tag."""
        app = create_app()
        mock_repo = MagicMock()
        mock_repo.create_tag = AsyncMock(side_effect=lambda t: t)
        app.dependency_overrides[get_repository] = lambda: mock_repo
        client = TestClient(app)

        response = client.post(
            "/taxonomy/tags",
            json={
                "category_id": "cat-1",
                "name": "Parts Delay",
                "slug": "parts-delay",
                "description": "Waiting on parts from supplier",
                "color": "#FF6B6B",
                "icon": "clock",
                "priority": 1,
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Parts Delay"
        assert data["slug"] == "parts-delay"
