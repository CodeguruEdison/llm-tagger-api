"""Unit tests for TagRuleCondition domain model."""
import pytest
from pydantic import ValidationError

from tagging.domain.enums import ConditionOperator, ConditionType
from tagging.domain.tag_rule_condition import TagRuleCondition


class TestTagRuleCondition:

    def _make_condition(self, **overrides) -> TagRuleCondition:
        defaults = dict(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered", "waiting on parts"],
        )
        return TagRuleCondition(**{**defaults, **overrides})

    def test_can_create_condition(self):
        condition = self._make_condition()
        assert condition.condition_type == ConditionType.KEYWORD_ANY
        assert len(condition.values) == 2

    def test_values_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            self._make_condition(values=[])

    def test_condition_is_immutable(self):
        condition = self._make_condition()
        with pytest.raises(ValidationError):
            condition.values = ["changed"]

    def test_serialize_to_dict(self):
        condition = self._make_condition()
        data = condition.model_dump()
        assert data["condition_type"] == "keyword_any"
        assert data["values"] == ["backordered", "waiting on parts"]