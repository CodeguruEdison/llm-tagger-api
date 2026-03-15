"""Unit tests for NoteContext domain model."""
import pytest
from pydantic import ValidationError

from tagging.domain.note_context import NoteContext


class TestNoteContext:

    def _make_context(self, **overrides) -> NoteContext:
        defaults = {
            "note_id": "note-1",
            "ro_id": "ro-1",
            "shop_id": "shop-1",
            "text": "waiting on parts from LKQ",
            "event_type": "note",
        }
        return NoteContext(**{**defaults, **overrides})

    def test_can_create_note_context(self):
        context = self._make_context()
        assert context.note_id == "note-1"
        assert context.text == "waiting on parts from LKQ"

    def test_text_cannot_be_empty(self):
        """
        Empty text cannot be tagged.
        Rules engine and LLM both need text to work with.
        """
        with pytest.raises(ValidationError):
            self._make_context(text="")

    def test_text_is_stripped(self):
        """
        Whitespace stripped automatically.
        LLM and rules engine get clean input.
        """
        context = self._make_context(text="  waiting on parts  ")
        assert context.text == "waiting on parts"

    def test_whitespace_only_text_fails(self):
        """Whitespace-only is effectively empty."""
        with pytest.raises(ValidationError):
            self._make_context(text="     ")

    def test_is_immutable(self):
        """NoteContext cannot be modified mid-pipeline."""
        context = self._make_context()
        with pytest.raises(ValidationError):
            context.text = "changed"

    def test_serialize_to_dict(self):
        """
        Must serialize for ARQ job queue.
        Why: ARQ serializes job arguments to Redis.
        NoteContext is the main job argument.
        """
        context = self._make_context()
        data = context.model_dump()
        assert data["note_id"] == "note-1"
        assert data["text"] == "waiting on parts from LKQ"

    def test_deserialize_from_dict(self):
        """Must reconstruct from Redis job queue data."""
        data = {
            "note_id": "note-1",
            "ro_id": "ro-1",
            "shop_id": "shop-1",
            "text": "waiting on parts from LKQ",
            "event_type": "note",
        }
        context = NoteContext.model_validate(data)
        assert context.note_id == "note-1"
        assert context.text == "waiting on parts from LKQ"
