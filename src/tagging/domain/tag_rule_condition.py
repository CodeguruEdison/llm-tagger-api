"""
TagRuleCondition domain model.
A single condition within a tagging rule.
"""
from pydantic import BaseModel, ConfigDict, field_validator

from tagging.domain.enums import ConditionOperator, ConditionType


class TagRuleCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    condition_type: ConditionType
    operator: ConditionOperator
    values: list[str]

    @field_validator("values")
    @classmethod
    def values_cannot_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("values cannot be empty")
        return v

    @classmethod
    def from_db(cls, row: dict) -> "TagRuleCondition":
        return cls.model_validate(row)