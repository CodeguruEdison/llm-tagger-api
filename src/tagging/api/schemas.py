"""
API request and response schemas.

Separate from domain models — API shapes can evolve
independently from the core domain.

Why separate schemas:
  - API can expose only what clients need
  - Domain models can change without breaking API contracts
  - Input validation happens here (Pydantic)
  - Output formatting happens here
"""
from typing import Optional
from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────

class TagNoteRequest(BaseModel):
    """Request body for POST /tag."""
    note_id: str
    ro_id: str
    shop_id: str
    text: str
    event_type: str = "note"

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text cannot be empty")
        return v.strip()


class CreateRuleConditionRequest(BaseModel):
    """Single condition within a rule creation request."""
    condition_type: str   # KEYWORD_ANY, KEYWORD_NONE, PHRASE, REGEX
    operator: str         # AND, OR
    values: list[str]

    @field_validator("values")
    @classmethod
    def values_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("values cannot be empty")
        return v


class CreateRuleRequest(BaseModel):
    """Request body for POST /rules."""
    tag_id: str
    name: str
    priority: int = 100
    is_enabled: bool = True
    conditions: list[CreateRuleConditionRequest]

    @field_validator("conditions")
    @classmethod
    def must_have_conditions(
        cls, v: list[CreateRuleConditionRequest]
    ) -> list[CreateRuleConditionRequest]:
        if not v:
            raise ValueError("rule must have at least one condition")
        return v


class UpdateRuleRequest(BaseModel):
    """Request body for PUT /rules/{rule_id}."""
    name: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None
    conditions: Optional[list[CreateRuleConditionRequest]] = None


# ─────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────

class TagResponse(BaseModel):
    """Single tag in API responses."""
    id: str
    category_id: str
    name: str
    slug: str
    description: str
    color: str
    icon: str
    priority: int
    is_active: bool


class TagResultResponse(BaseModel):
    """Single tag result from the tagging pipeline."""
    tag: TagResponse
    confidence: float
    source: str       # RULES or LLM
    reasoning: str


class TagNoteResponse(BaseModel):
    """Response body for POST /tag."""
    note_id: str
    results: list[TagResultResponse]
    total: int


class RuleConditionResponse(BaseModel):
    """Single condition in rule responses."""
    id: str
    condition_type: str
    operator: str
    values: list[str]


class RuleResponse(BaseModel):
    """Single rule in API responses."""
    id: str
    tag_id: str
    name: str
    priority: int
    is_enabled: bool
    conditions: list[RuleConditionResponse]


class CategoryResponse(BaseModel):
    """Single category in taxonomy responses."""
    id: str
    name: str
    slug: str
    description: str
    is_active: bool
    sort_order: int


class TaxonomyResponse(BaseModel):
    """Full taxonomy response."""
    categories: list[CategoryResponse]
    tags: list[TagResponse]
    total_categories: int
    total_tags: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "0.1.0"