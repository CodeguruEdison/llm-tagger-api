"""
Tagging router.

POST /tag — submit a note, get back tags
"""
from fastapi import APIRouter, Depends

from tagging.api.dependencies import get_orchestrator
from tagging.api.schemas import (
    TagNoteRequest,
    TagNoteResponse,
    TagResponse,
    TagResultResponse,
)
from tagging.application.orchestrator import Orchestrator
from tagging.domain.note_context import NoteContext

router = APIRouter(tags=["tagging"])


@router.post("/tag", response_model=TagNoteResponse)
async def tag_note(
    request: TagNoteRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> TagNoteResponse:
    """
    Tag a repair order note.

    Runs the full pipeline:
      1. Rules engine (fast path)
      2. LLM (if configured)
      3. Merge and deduplicate results

    Returns all matched tags with confidence and reasoning.
    """
    context = NoteContext(
        note_id=request.note_id,
        ro_id=request.ro_id,
        shop_id=request.shop_id,
        text=request.text,
        event_type=request.event_type,
    )

    results = await orchestrator.tag_note(context)

    return TagNoteResponse(
        note_id=request.note_id,
        results=[
            TagResultResponse(
                tag=TagResponse(
                    id=r.tag.id,
                    category_id=r.tag.category_id,
                    name=r.tag.name,
                    slug=r.tag.slug,
                    description=r.tag.description,
                    color=r.tag.color,
                    icon=r.tag.icon,
                    priority=r.tag.priority,
                    is_active=r.tag.is_active,
                ),
                confidence=r.confidence,
                source=r.source.value.upper(),
                reasoning=r.reasoning,
            )
            for r in results
        ],
        total=len(results),
    )
