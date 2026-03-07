"""
Domain enums — all system-wide constants in one place.

Why enums over plain strings:
  - IDE autocomplete — no typos
  - Fail fast on invalid values
  - Self-documenting code
  - DB stores the .value (string) — clean and readable
"""
from enum import Enum


class ConditionType(str, Enum):
    """
    How a rule condition matches against note text.

    KEYWORD_ANY:  match if ANY keyword in values list is found
                  e.g. values=["backordered", "waiting on parts"]
                  → matches if either word appears

    KEYWORD_NONE: match if NONE of the keywords are found
                  e.g. values=["parts arrived", "parts received"]
                  → used to EXCLUDE false positives

    PHRASE:       exact phrase match (case insensitive)
                  e.g. values=["waiting on parts from"]
                  → must appear as a complete phrase

    REGEX:        regular expression pattern
                  e.g. values=["ETA.*days", "back.?ordered"]
                  → most powerful, most complex
    """
    KEYWORD_ANY = "keyword_any"
    KEYWORD_NONE = "keyword_none"
    PHRASE = "phrase"
    REGEX = "regex"


class ConditionOperator(str, Enum):
    """
    How multiple conditions in a rule combine.

    AND: ALL conditions must pass → tag applied
         e.g. contains "backordered" AND NOT contains "parts arrived"

    OR:  ANY condition passing → tag applied
         e.g. contains "backordered" OR contains "waiting on parts"
    """
    AND = "and"
    OR = "or"


class TaggingMode(str, Enum):
    """
    Controls which parts of the tagging pipeline are active.

    RULES_ONLY:  only keyword/regex rules engine runs
                 → fastest, free, deterministic
                 → use when: cost sensitive, LLM unavailable,
                             or during development/testing

    LLM_ONLY:    only LLM chain runs, rules engine skipped
                 → smartest, handles typos and context
                 → use when: testing LLM prompts in isolation,
                             or rules engine not yet configured

    HYBRID:      rules engine runs first (fast path)
                 LLM runs for unmatched or low confidence results
                 → best accuracy + reasonable cost
                 → default for production
    """
    RULES_ONLY = "rules_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"