"""ConditionOperator enum — how conditions combine."""

from enum import StrEnum


class ConditionOperator(StrEnum):
    AND = "and"
    OR = "or"
