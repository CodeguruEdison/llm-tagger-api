"""Unit tests for TagResult domain model."""

import pytest
from pydantic import ValidationError

from tagging.domain.enums import TagSource
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult


class TestTagResult:
    def _make_tag(self) -> Tag:
        return Tag(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO is waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )

    def _make_result(self, **overrides) -> TagResult:
        defaults = {
            "tag": self._make_tag(),
            "confidence": 1.0,
            "source": TagSource.RULES,
            "reasoning": "matched rule: Parts Delay Detection",
        }
        return TagResult(**{**defaults, **overrides})

    def test_can_create_rules_result(self):
        """
        Rules engine result.
        Confidence always 1.0 — deterministic match.
        """
        result = self._make_result()
        assert result.tag.slug == "parts-delay"
        assert result.confidence == 1.0
        assert result.source == TagSource.RULES

    def test_can_create_llm_result(self):
        """
        LLM result.
        Confidence between 0 and 1 — probabilistic.
        """
        result = self._make_result(
            confidence=0.92,
            source=TagSource.LLM,
            reasoning="note indicates parts procurement delay",
        )
        assert result.confidence == 0.92
        assert result.source == TagSource.LLM

    def test_confidence_cannot_exceed_1(self):
        """Confidence is a probability — max 1.0."""
        with pytest.raises(ValidationError):
            self._make_result(confidence=1.5)

    def test_confidence_cannot_be_negative(self):
        """Confidence cannot be negative."""
        with pytest.raises(ValidationError):
            self._make_result(confidence=-0.1)

    def test_reasoning_cannot_be_empty(self):
        """
        Reasoning must always be provided.
        Why: shown in Langfuse traces and RO detail view.
        Without it, debugging why a tag was applied
        is impossible at scale.
        """
        with pytest.raises(ValidationError):
            self._make_result(reasoning="")

    def test_is_immutable(self):
        """TagResult cannot be modified after creation."""
        result = self._make_result()
        with pytest.raises(ValidationError):
            result.confidence = 0.5

    def test_serialize_to_dict(self):
        """Must serialize for DB persistence and API response."""
        result = self._make_result()
        data = result.model_dump()
        assert data["confidence"] == 1.0
        assert data["source"] == "rules"
        assert data["tag"]["slug"] == "parts-delay"
