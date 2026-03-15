"""
Rules router — CRUD for tagging rules.

GET    /rules              ← list all rules
GET    /rules/{rule_id}    ← get single rule
POST   /rules              ← create rule
PUT    /rules/{rule_id}    ← update rule
DELETE /rules/{rule_id}    ← delete rule
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from tagging.api.dependencies import get_repository
from tagging.api.schemas import (
    CreateRuleRequest,
    RuleConditionResponse,
    RuleResponse,
    UpdateRuleRequest,
)
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition
from tagging.infrastructure.db.repository import TagRepository

router = APIRouter(prefix="/rules", tags=["rules"])


def _rule_to_response(rule: TagRule) -> RuleResponse:
    """Convert domain TagRule to API response."""
    return RuleResponse(
        id=rule.id,
        tag_id=rule.tag_id,
        name=rule.name,
        priority=rule.priority,
        is_enabled=rule.is_enabled,
        conditions=[
            RuleConditionResponse(
                id=c.id,
                condition_type=c.condition_type.value,
                operator=c.operator.value,
                values=c.values,
            )
            for c in rule.conditions
        ],
    )


@router.get("", response_model=list[RuleResponse])
async def get_rules(
    repository: TagRepository = Depends(get_repository),
) -> list[RuleResponse]:
    """List all rules."""
    rules = await repository.get_all_rules()
    return [_rule_to_response(r) for r in rules]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    repository: TagRepository = Depends(get_repository),
) -> RuleResponse:
    """Get a single rule by ID."""
    rule = await repository.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )
    return _rule_to_response(rule)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: CreateRuleRequest,
    repository: TagRepository = Depends(get_repository),
) -> RuleResponse:
    """Create a new tagging rule."""
    rule = TagRule(
        id=str(uuid.uuid4()),
        tag_id=request.tag_id,
        name=request.name,
        priority=request.priority,
        is_enabled=request.is_enabled,
        conditions=[
            TagRuleCondition(
                id=str(uuid.uuid4()),
                condition_type=ConditionType(request_cond.condition_type.lower()),
                operator=ConditionOperator(request_cond.operator.lower()),
                values=request_cond.values,
            )
            for request_cond in request.conditions
        ],
    )
    created = await repository.create_rule(rule)
    return _rule_to_response(created)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    repository: TagRepository = Depends(get_repository),
) -> RuleResponse:
    """Update an existing rule."""
    existing = await repository.get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )

    # Apply partial updates
    updated = TagRule(
        id=existing.id,
        tag_id=existing.tag_id,
        name=request.name if request.name is not None else existing.name,
        priority=request.priority
        if request.priority is not None
        else existing.priority,
        is_enabled=request.is_enabled
        if request.is_enabled is not None
        else existing.is_enabled,
        conditions=[
            TagRuleCondition(
                id=str(uuid.uuid4()),
                condition_type=ConditionType(c.condition_type),
                operator=ConditionOperator(c.operator),
                values=c.values,
            )
            for c in request.conditions
        ]
        if request.conditions is not None
        else existing.conditions,
    )

    saved = await repository.update_rule(updated)
    return _rule_to_response(saved)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    repository: TagRepository = Depends(get_repository),
) -> None:
    """Delete a rule and all its conditions."""
    existing = await repository.get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )
    await repository.delete_rule(rule_id)
