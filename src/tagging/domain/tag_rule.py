"""
TagRule domain model.
Defines when a tag should be applied.
Evaluated by rules engine in priority order.
"""
from pydantic import BaseModel, ConfigDict, field_validator

from tagging.domain.tag_rule_condition import TagRuleCondition


class TagRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tag_id: str
    name: str
    priority: int
    is_enabled: bool
    conditions: list[TagRuleCondition]

    @field_validator("name")
    @classmethod
    def name_cannot_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def priority_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("priority must be >= 1")
        return v

    @field_validator("conditions")
    @classmethod
    def must_have_at_least_one_condition(
        cls, v: list[TagRuleCondition]
    ) -> list[TagRuleCondition]:
        if not v:
            raise ValueError(
                "a rule must have at least one condition. "
                "A rule with no conditions would match every note."
            )
        return v

    @classmethod
    def from_db(cls, row: dict) -> "TagRule":
        return cls.model_validate(row)