"""
TagResult domain model.
The output from the tagging pipeline.

Every layer of the system speaks TagResult out:
  - Pipeline → TagResult
  - DB persistence → TagResult
  - API response → TagResult
  - WebSocket push → TagResult
"""
from pydantic import BaseModel, ConfigDict, field_validator

from tagging.domain.enums import TagSource
from tagging.domain.tag import Tag


class TagResult(BaseModel):
    """
    Represents a tag applied to a note by the pipeline.

    Contains:
      - which tag was applied
      - how confident we are (1.0 for rules, 0-1 for LLM)
      - which part of pipeline applied it
      - why it was applied (for observability)

    Immutable — result is final once created.
    """
    model_config = ConfigDict(frozen=True)

    tag: Tag
    confidence: float
    source: TagSource
    reasoning: str

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_valid(cls, v: float) -> float:
        """
        Confidence is a probability score: 0.0 to 1.0
        Rules engine always returns 1.0 (deterministic)
        LLM returns 0.0-1.0 (probabilistic)
        """
        if v < 0.0 or v > 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0. Got: {v}"
            )
        return v

    @field_validator("reasoning")
    @classmethod
    def reasoning_cannot_be_empty(cls, v: str) -> str:
        """
        Reasoning is required for observability.
        Shows in Langfuse traces and RO detail view.
        Without it debugging is impossible at scale.
        """
        if not v or not v.strip():
            raise ValueError("reasoning cannot be empty")
        return v.strip()