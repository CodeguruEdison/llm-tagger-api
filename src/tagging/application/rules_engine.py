"""
Rules Engine — fast path of the tagging pipeline.

Evaluates keyword/regex rules against note text.
Zero I/O — pure Python logic.
Must be fast: target <1ms per note.

Pipeline position:
  NoteContext → RulesEngine → list[TagResult] → TagMerger
"""
import re

from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


class RulesEngine:
    """
    Evaluates all active rules against a note.

    For each rule:
      1. Skip if disabled
      2. Evaluate all conditions
      3. If all pass → create TagResult
      4. Return all matching TagResults

    Confidence is always 1.0 — rules are deterministic.
    Either the keyword is there or it isn't.
    """

    def evaluate(
        self,
        context: NoteContext,
        tags: list[Tag],
        rules: list[TagRule],
    ) -> list[TagResult]:
        """
        Evaluate all rules against the note text.

        Args:
            context: the note being tagged
            tags:    all active tags (to look up by tag_id)
            rules:   all active rules to evaluate

        Returns:
            list of TagResult for every rule that matched
        """
        # Build tag lookup by id for O(1) access
        tag_by_id = {tag.id: tag for tag in tags}

        results = []
        text = context.text.lower()  # normalize once, reuse

        for rule in rules:
            if not rule.is_enabled:
                continue

            tag = tag_by_id.get(rule.tag_id)
            if not tag:
                continue

            if self._evaluate_rule(rule, text):
                results.append(
                    TagResult(
                        tag=tag,
                        confidence=1.0,
                        source=TagSource.RULES,
                        reasoning=f"matched rule: {rule.name}",
                    )
                )

        return results

    def _evaluate_rule(
        self,
        rule: TagRule,
        text: str,
    ) -> bool:
        """
        All conditions must pass for the rule to match.
        This implements the AND operator between conditions.
        """
        return all(
            self._evaluate_condition(condition, text)
            for condition in rule.conditions
        )

    def _evaluate_condition(
        self,
        condition: TagRuleCondition,
        text: str,
    ) -> bool:
        """
        Evaluate a single condition against the note text.
        Dispatches to the correct matching strategy.
        """
        match condition.condition_type:
            case ConditionType.KEYWORD_ANY:
                return self._keyword_any(condition.values, text)

            case ConditionType.KEYWORD_NONE:
                return self._keyword_none(condition.values, text)

            case ConditionType.PHRASE:
                return self._phrase(condition.values, text)

            case ConditionType.REGEX:
                return self._regex(condition.values, text)

        return False

    def _keyword_any(
        self, keywords: list[str], text: str
    ) -> bool:
        """
        Returns True if ANY keyword is found in text.
        Case insensitive — technicians type in all caps sometimes.
        """
        return any(
            keyword.lower() in text
            for keyword in keywords
        )

    def _keyword_none(
        self, keywords: list[str], text: str
    ) -> bool:
        """
        Returns True if NONE of the keywords are found.
        Used to exclude false positives.

        Example:
          values: ["parts arrived", "parts received"]
          text:   "waiting on parts"
          result: True  (neither exclusion keyword found)

          text:   "waiting on parts — parts arrived today"
          result: False (exclusion keyword found → block tag)
        """
        return not any(
            keyword.lower() in text
            for keyword in keywords
        )

    def _phrase(
        self, phrases: list[str], text: str
    ) -> bool:
        """
        Returns True if ANY exact phrase is found.
        Case insensitive.
        """
        return any(
            phrase.lower() in text
            for phrase in phrases
        )

    def _regex(
        self, patterns: list[str], text: str
    ) -> bool:
        """
        Returns True if ANY regex pattern matches.
        Case insensitive flag applied automatically.

        Why re.search not re.match:
          re.match only checks the start of string
          re.search checks anywhere in the string
          Notes are free-form text — search is correct.
        """
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        )
