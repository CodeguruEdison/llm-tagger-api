
from tagging.application.rules_engine import RulesEngine
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


class TestRulesEngine:

    def _make_tag(self, slug="parts-delay") -> Tag:
        return Tag(
            id="tag-1",
            category_id="cat-1",
            name="Parts Delay",
            slug=slug,
            description="RO waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )

    def _make_context(self, text: str) -> NoteContext:
        return NoteContext(
            note_id="note-1",
            ro_id="ro-1",
            shop_id="shop-1",
            text=text,
            event_type="note",
        )

    def _make_rule(
        self,
        conditions: list[TagRuleCondition],
        tag: Tag = None,
    ) -> TagRule:
        return TagRule(
            id="rule-1",
            tag_id="tag-1",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=conditions,
        )

    # ─── KEYWORD_ANY tests ───────────────────────

    def test_keyword_any_matches_when_keyword_found(self):
        """KEYWORD_ANY passes when any keyword is in the note."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered", "waiting on parts"],
                )
            ],
        )
        context = self._make_context("waiting on parts from LKQ")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1
        assert results[0].tag.slug == "parts-delay"
        assert results[0].source == TagSource.RULES
        assert results[0].confidence == 1.0

    def test_keyword_any_no_match_when_no_keywords(self):
        """KEYWORD_ANY fails when no keywords found."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered", "waiting on parts"],
                )
            ],
        )
        context = self._make_context("customer called about status update")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 0

    def test_keyword_any_case_insensitive(self):
        """
        Keyword matching must be case insensitive.
        'BACKORDERED' should match 'backordered'.
        Technicians type in all caps sometimes.
        """
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered"],
                )
            ],
        )
        context = self._make_context("PART IS BACKORDERED FROM SUPPLIER")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1

    # ─── KEYWORD_NONE tests ──────────────────────

    def test_keyword_none_passes_when_no_keywords(self):
        """KEYWORD_NONE passes when none of the keywords are found."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_NONE,
                    operator=ConditionOperator.AND,
                    values=["parts arrived", "parts received"],
                )
            ],
        )
        context = self._make_context("waiting on parts from supplier")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1

    def test_keyword_none_fails_when_keyword_found(self):
        """KEYWORD_NONE fails when any excluded keyword is found."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_NONE,
                    operator=ConditionOperator.AND,
                    values=["parts arrived", "parts received"],
                )
            ],
        )
        context = self._make_context("parts arrived this morning")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 0

    # ─── PHRASE tests ────────────────────────────

    def test_phrase_matches_exact_phrase(self):
        """PHRASE matches exact phrase regardless of case."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.PHRASE,
                    operator=ConditionOperator.AND,
                    values=["waiting on parts from"],
                )
            ],
        )
        context = self._make_context("waiting on parts from LKQ supplier")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1

    def test_phrase_no_match_partial(self):
        """PHRASE does not match partial phrases."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.PHRASE,
                    operator=ConditionOperator.AND,
                    values=["waiting on parts from supplier"],
                )
            ],
        )
        context = self._make_context("waiting on parts from LKQ")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 0

    # ─── REGEX tests ─────────────────────────────

    def test_regex_matches_pattern(self):
        """REGEX matches regular expression patterns."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.REGEX,
                    operator=ConditionOperator.AND,
                    values=[r"ETA.*\d+ days"],
                )
            ],
        )
        context = self._make_context("ETA is 5 days from supplier")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1

    def test_regex_no_match(self):
        """REGEX returns no match when pattern not found."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.REGEX,
                    operator=ConditionOperator.AND,
                    values=[r"ETA.*\d+ days"],
                )
            ],
        )
        context = self._make_context("waiting on parts")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 0

    # ─── Multiple conditions tests ───────────────

    def test_multiple_conditions_all_must_pass(self):
        """
        All AND conditions must pass for tag to apply.
        This is the core deduplication logic.
        """
        engine = RulesEngine()
        tag = self._make_tag()
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
            ],
        )

        # Both conditions pass
        context = self._make_context("waiting on parts from supplier")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1

        # Second condition fails
        context2 = self._make_context(
            "waiting on parts — UPDATE: parts arrived"
        )
        results2 = engine.evaluate(context2, [tag], [rule])
        assert len(results2) == 0

    # ─── Multiple rules tests ────────────────────

    def test_multiple_rules_can_match(self):
        """
        Multiple rules can match the same note.
        Each matching rule produces a TagResult.
        """
        engine = RulesEngine()

        tag1 = self._make_tag(slug="parts-delay")
        tag2 = Tag(
            id="tag-2",
            category_id="cat-1",
            name="Customer Concern",
            slug="customer-concern",
            description="Customer issue",
            color="#3B82F6",
            icon="user",
            priority=1,
            is_active=True,
        )

        rule1 = TagRule(
            id="rule-1",
            tag_id="tag-1",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["waiting on parts"],
                )
            ],
        )
        rule2 = TagRule(
            id="rule-2",
            tag_id="tag-2",
            name="Customer Concern Detection",
            priority=90,
            is_enabled=True,
            conditions=[
                TagRuleCondition(
                    id="cond-2",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["customer upset", "customer called"],
                )
            ],
        )

        context = self._make_context(
            "waiting on parts, customer called twice"
        )
        results = engine.evaluate(context, [tag1, tag2], [rule1, rule2])
        assert len(results) == 2
        slugs = [r.tag.slug for r in results]
        assert "parts-delay" in slugs
        assert "customer-concern" in slugs

    def test_disabled_rule_is_skipped(self):
        """Disabled rules must never apply tags."""
        engine = RulesEngine()
        tag = self._make_tag()
        rule = TagRule(
            id="rule-1",
            tag_id="tag-1",
            name="Disabled Rule",
            priority=100,
            is_enabled=False,       # disabled
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["waiting on parts"],
                )
            ],
        )
        context = self._make_context("waiting on parts from supplier")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 0

    def test_returns_reasoning_with_rule_name(self):
        """
        TagResult must include reasoning.
        Shows which rule matched — critical for observability.
        """
        engine = RulesEngine()
        tag = self._make_tag()
        rule = self._make_rule(
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered"],
                )
            ],
        )
        context = self._make_context("part is backordered")
        results = engine.evaluate(context, [tag], [rule])
        assert len(results) == 1
        assert "Parts Delay Detection" in results[0].reasoning
