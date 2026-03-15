"""Unit tests for TagRule domain model."""

import pytest
from pydantic import ValidationError

from tagging.domain.enums import ConditionOperator, ConditionType
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


class TestTagRule:
    def _make_condition(self) -> TagRuleCondition:
        return TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered", "waiting on parts"],
        )

    def _make_rule(self, **overrides) -> TagRule:
        defaults = {
            "id": "rule-1",
            "tag_id": "uuid-2",
            "name": "Parts Delay Detection",
            "priority": 100,
            "is_enabled": True,
            "conditions": [self._make_condition()],
        }
        return TagRule(**{**defaults, **overrides})

    def test_can_create_rule(self):
        rule = self._make_rule()
        assert rule.name == "Parts Delay Detection"
        assert rule.priority == 100
        assert len(rule.conditions) == 1

    def test_must_have_at_least_one_condition(self):
        with pytest.raises(ValidationError):
            self._make_rule(conditions=[])

    def test_priority_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make_rule(priority=0)

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            self._make_rule(name="")

    def test_rule_is_immutable(self):
        rule = self._make_rule()
        with pytest.raises(ValidationError):
            rule.name = "Changed"

    def test_rule_with_multiple_conditions(self):
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered", "waiting on parts"],
                ),
                TagRuleCondition(
                    id="cond-2",
                    condition_type=ConditionType.KEYWORD_NONE,
                    operator=ConditionOperator.AND,
                    values=["parts arrived", "parts received"],
                ),
            ]
        )
        assert len(rule.conditions) == 2

    def test_serialize_to_dict(self):
        rule = self._make_rule()
        data = rule.model_dump()
        assert data["name"] == "Parts Delay Detection"
        assert data["priority"] == 100
        assert len(data["conditions"]) == 1
