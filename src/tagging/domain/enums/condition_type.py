"""ConditionType enum — how a rule condition matches text."""
from enum import StrEnum


class ConditionType(StrEnum):
    KEYWORD_ANY = "keyword_any"
    KEYWORD_NONE = "keyword_none"
    PHRASE = "phrase"
    REGEX = "regex"
