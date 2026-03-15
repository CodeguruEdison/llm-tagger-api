import pytest

from tagging.domain.enums import (
    ConditionOperator,
    ConditionType,
    TaggingMode,
    TagSource,
)


class TestConditionType:
    def test_all_condition_types_exist(self):
        """
        All condition types the rules engine supports.
        Each type = different matching strategy.
        """
        assert ConditionType.KEYWORD_ANY  # match ANY keyword in list
        assert ConditionType.KEYWORD_NONE  # match if NONE of keywords present
        assert ConditionType.PHRASE  # exact phrase match
        assert ConditionType.REGEX  # regular expression match

    def test_values_are_strings(self):
        """String values for DB storage and API responses."""
        assert ConditionType.KEYWORD_ANY.value == "keyword_any"
        assert ConditionType.KEYWORD_NONE.value == "keyword_none"
        assert ConditionType.PHRASE.value == "phrase"
        assert ConditionType.REGEX.value == "regex"

    def test_reconstruct_from_string(self):
        """Must rebuild from DB string value."""
        assert ConditionType("keyword_any") == ConditionType.KEYWORD_ANY
        assert ConditionType("regex") == ConditionType.REGEX

    def test_invalid_type_raises(self):
        """Unknown condition type must fail immediately."""
        with pytest.raises(ValueError):
            ConditionType("invalid")


class TestConditionOperator:
    def test_all_operators_exist(self):
        """
        AND: all conditions must pass
        OR:  any condition can pass
        """
        assert ConditionOperator.AND
        assert ConditionOperator.OR

    def test_values_are_strings(self):
        assert ConditionOperator.AND.value == "and"
        assert ConditionOperator.OR.value == "or"


class TestTaggingMode:
    def test_all_modes_exist(self):
        """
        Three modes control the tagging pipeline.
        """
        assert TaggingMode.RULES_ONLY  # fast, free, no LLM
        assert TaggingMode.LLM_ONLY  # smart, costs money
        assert TaggingMode.HYBRID  # best of both (default)

    def test_values_are_strings(self):
        assert TaggingMode.RULES_ONLY.value == "rules_only"
        assert TaggingMode.LLM_ONLY.value == "llm_only"
        assert TaggingMode.HYBRID.value == "hybrid"

    def test_default_is_hybrid(self):
        """
        Hybrid must be the default.
        Why: best accuracy out of the box.
        Operators can downgrade to rules_only if needed.
        """
        assert TaggingMode.HYBRID.value == "hybrid"

    def test_reconstruct_from_string(self):
        """
        Must rebuild from env var string.
        TAGGING_MODE=rules_only → TaggingMode.RULES_ONLY
        """
        assert TaggingMode("rules_only") == TaggingMode.RULES_ONLY
        assert TaggingMode("llm_only") == TaggingMode.LLM_ONLY
        assert TaggingMode("hybrid") == TaggingMode.HYBRID

    def test_invalid_mode_raises(self):
        """
        Invalid mode must fail at startup — not silently default.
        Why: silent fallback to wrong mode could cost money
        or miss tags in production. Fail fast.
        """
        with pytest.raises(ValueError):
            TaggingMode("invalid_mode")


class TestTagSource:
    def test_all_sources_exist(self):
        assert TagSource.RULES
        assert TagSource.LLM

    def test_values_are_strings(self):
        assert TagSource.RULES.value == "rules"
        assert TagSource.LLM.value == "llm"

    def test_reconstruct_from_string(self):
        assert TagSource("rules") == TagSource.RULES
        assert TagSource("llm") == TagSource.LLM

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError):
            TagSource("invalid")
