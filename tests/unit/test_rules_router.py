"""Unit tests for rules router."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from tagging.api.app import create_app
from tagging.api.dependencies import get_repository
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


def make_rule(rule_id="rule-1") -> TagRule:
    return TagRule(
        id=rule_id,
        tag_id="tag-1",
        name="Parts Delay Detection",
        priority=100,
        is_enabled=True,
        conditions=[
            TagRuleCondition(
                id="cond-1",
                condition_type=ConditionType.KEYWORD_ANY,
                operator=ConditionOperator.AND,
                values=["backordered", "waiting on parts"],
            )
        ],
    )


def make_client(rules=None, rule=None):
    app = create_app()
    mock_repo = MagicMock()
    mock_repo.get_all_rules = AsyncMock(return_value=rules or [])
    mock_repo.get_rule_by_id = AsyncMock(return_value=rule)
    mock_repo.create_rule = AsyncMock(side_effect=lambda r: r)
    mock_repo.update_rule = AsyncMock(side_effect=lambda r: r)
    mock_repo.delete_rule = AsyncMock(return_value=None)
    app.dependency_overrides[get_repository] = lambda: mock_repo
    return TestClient(app), mock_repo


class TestRulesRouter:
    def test_get_rules(self):
        """GET /rules returns list of rules."""
        client, _ = make_client(rules=[make_rule()])
        response = client.get("/rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Parts Delay Detection"
        assert data[0]["conditions"][0]["values"] == ["backordered", "waiting on parts"]

    def test_get_rule_by_id(self):
        """GET /rules/{id} returns single rule."""
        client, _ = make_client(rule=make_rule())
        response = client.get("/rules/rule-1")
        assert response.status_code == 200
        assert response.json()["id"] == "rule-1"

    def test_get_rule_not_found(self):
        """GET /rules/{id} returns 404 when not found."""
        client, _ = make_client(rule=None)
        response = client.get("/rules/nonexistent")
        assert response.status_code == 404

    def test_create_rule(self):
        """POST /rules creates and returns new rule."""
        client, _ = make_client()
        response = client.post(
            "/rules",
            json={
                "tag_id": "tag-1",
                "name": "New Rule",
                "priority": 100,
                "is_enabled": True,
                "conditions": [
                    {
                        "condition_type": "KEYWORD_ANY",
                        "operator": "AND",
                        "values": ["backordered"],
                    }
                ],
            },
        )
        assert response.status_code == 201
        assert response.json()["name"] == "New Rule"

    def test_create_rule_empty_conditions_returns_422(self):
        """POST /rules with empty conditions returns 422."""
        client, _ = make_client()
        response = client.post(
            "/rules",
            json={
                "tag_id": "tag-1",
                "name": "Bad Rule",
                "conditions": [],
            },
        )
        assert response.status_code == 422

    def test_update_rule(self):
        """PUT /rules/{id} updates and returns rule."""
        client, _ = make_client(rule=make_rule())
        response = client.put(
            "/rules/rule-1",
            json={
                "name": "Updated Rule",
                "is_enabled": False,
            },
        )
        assert response.status_code == 200

    def test_update_rule_not_found(self):
        """PUT /rules/{id} returns 404 when not found."""
        client, _ = make_client(rule=None)
        response = client.put(
            "/rules/nonexistent",
            json={
                "name": "Updated",
            },
        )
        assert response.status_code == 404

    def test_delete_rule(self):
        """DELETE /rules/{id} returns 204."""
        client, _ = make_client(rule=make_rule())
        response = client.delete("/rules/rule-1")
        assert response.status_code == 204

    def test_delete_rule_not_found(self):
        """DELETE /rules/{id} returns 404 when not found."""
        client, _ = make_client(rule=None)
        response = client.delete("/rules/nonexistent")
        assert response.status_code == 404
