"""ConditionOperator enum — how conditions combine."""
from enum import Enum


class ConditionOperator(str, Enum):
    AND = "and"
    OR = "or"