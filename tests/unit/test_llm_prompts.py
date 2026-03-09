"""Unit tests for LLM prompt templates."""
import pytest
from pathlib import Path

from tagging.infrastructure.llm.prompts import (
    build_taxonomy_context,
    build_tagging_prompt,
    TAGGING_PROMPT,
    _load_template,
)
from tagging.domain.tag import Tag


class TestLoadTemplate:

    def test_loads_system_template(self):
        """System template loads from system.md."""
        content = _load_template("system.md")
        assert len(content) > 0
        assert "{taxonomy}" in content

    def test_loads_user_template(self):
        """User template loads from user.md."""
        content = _load_template("user.md")
        assert len(content) > 0
        assert "{note_text}" in content

    def test_missing_template_raises(self):
        """Missing template file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _load_template("nonexistent.md")


class TestBuildTaxonomyContext:

    def _make_tag(self, slug: str, description: str) -> Tag:
        return Tag(
            id=f"tag-{slug}",
            category_id="cat-1",
            name=slug.replace("-", " ").title(),
            slug=slug,
            description=description,
            color="#FF6B6B",
            icon="tag",
            priority=1,
            is_active=True,
        )

    def test_builds_taxonomy_string(self):
        """Taxonomy string includes slug and description."""
        tags = [
            self._make_tag(
                "parts-delay",
                "Waiting on parts from supplier",
            ),
            self._make_tag(
                "customer-concern",
                "Customer expressed dissatisfaction",
            ),
        ]
        result = build_taxonomy_context(tags)
        assert "parts-delay" in result
        assert "Waiting on parts from supplier" in result
        assert "customer-concern" in result

    def test_empty_tags_returns_message(self):
        """Empty taxonomy returns clear message."""
        result = build_taxonomy_context([])
        assert result == "No tags available."

    def test_each_tag_on_own_line(self):
        """Each tag is on its own line."""
        tags = [
            self._make_tag("parts-delay", "Parts issue"),
            self._make_tag("customer-concern", "Customer issue"),
        ]
        result = build_taxonomy_context(tags)
        lines = result.strip().split("\n")
        assert len(lines) == 2


class TestTaggingPrompt:

    def test_prompt_has_required_variables(self):
        """Prompt must have taxonomy and note_text variables."""
        variables = TAGGING_PROMPT.input_variables
        assert "taxonomy" in variables
        assert "note_text" in variables

    def test_prompt_can_be_formatted(self):
        """Prompt formats correctly with valid inputs."""
        messages = TAGGING_PROMPT.format_messages(
            taxonomy="  - parts-delay: Waiting on parts",
            note_text="waiting on parts from LKQ",
        )
        assert len(messages) == 2
        assert "parts-delay" in messages[0].content
        assert "waiting on parts from LKQ" in messages[1].content