"""Unit tests for API schemas."""
import pytest
from pydantic import ValidationError

from tagging.api.schemas import (
    CreateRuleConditionRequest,
    CreateRuleRequest,
    TagNoteRequest,
)


class TestTagNoteRequest:

    def test_valid_request(self):
        """Valid request parses correctly."""
        req = TagNoteRequest(
            note_id="note-1",
            ro_id="ro-1",
            shop_id="shop-1",
            text="waiting on parts from LKQ",
        )
        assert req.note_id == "note-1"
        assert req.event_type == "note"

    def test_text_stripped(self):
        """Text is stripped of whitespace."""
        req = TagNoteRequest(
            note_id="note-1",
            ro_id="ro-1",
            shop_id="shop-1",
            text="  waiting on parts  ",
        )
        assert req.text == "waiting on parts"

    def test_empty_text_raises(self):
        """Empty text raises ValidationError."""
        with pytest.raises(ValidationError):
            TagNoteRequest(
                note_id="note-1",
                ro_id="ro-1",
                shop_id="shop-1",
                text="   ",
            )


class TestCreateRuleRequest:

    def test_valid_request(self):
        """Valid rule request parses correctly."""
        req = CreateRuleRequest(
            tag_id="tag-1",
            name="Parts Delay Detection",
            conditions=[
                CreateRuleConditionRequest(
                    condition_type="KEYWORD_ANY",
                    operator="AND",
                    values=["backordered"],
                )
            ],
        )
        assert req.name == "Parts Delay Detection"
        assert req.priority == 100
        assert req.is_enabled is True

    def test_empty_conditions_raises(self):
        """Rule with no conditions raises ValidationError."""
        with pytest.raises(ValidationError):
            CreateRuleRequest(
                tag_id="tag-1",
                name="Bad Rule",
                conditions=[],
            )

    def test_empty_values_raises(self):
        """Condition with empty values raises ValidationError."""
        with pytest.raises(ValidationError):
            CreateRuleRequest(
                tag_id="tag-1",
                name="Bad Rule",
                conditions=[
                    CreateRuleConditionRequest(
                        condition_type="KEYWORD_ANY",
                        operator="AND",
                        values=[],
                    )
                ],
            )
