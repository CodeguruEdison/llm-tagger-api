"""
NoteContext domain model.
The input to the tagging pipeline.

Every layer of the system speaks NoteContext in:
  - HTTP request → NoteContext
  - ARQ job queue → NoteContext
  - Tests → NoteContext
"""
from pydantic import BaseModel, ConfigDict, field_validator


class NoteContext(BaseModel):
    """
    Represents a note or event entering the tagging pipeline.

    Immutable — created once, passed through pipeline unchanged.
    Every layer reads from it, nothing modifies it.
    """
    model_config = ConfigDict(frozen=True)

    note_id: str
    ro_id: str
    shop_id: str
    text: str
    event_type: str

    @field_validator("text")
    @classmethod
    def text_cannot_be_empty(cls, v: str) -> str:
        """
        Strip whitespace first, then check for empty.
        Why: '   ' and '' are both meaningless to the pipeline.
        Clean text = better LLM results + accurate rule matching.
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("text cannot be empty or whitespace only")
        return stripped

    @classmethod
    def from_dict(cls, data: dict) -> "NoteContext":
        """Reconstruct from ARQ job queue data."""
        return cls.model_validate(data)
