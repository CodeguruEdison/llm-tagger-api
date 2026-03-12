"""
Taxonomy router.

GET /taxonomy              ← all categories + tags
GET /taxonomy/categories   ← list categories
GET /taxonomy/tags         ← list all tags
"""
from fastapi import APIRouter, Depends

from tagging.api.dependencies import get_repository
from tagging.api.schemas import (
    CategoryResponse,
    TagResponse,
    TaxonomyResponse,
)
from tagging.infrastructure.db.repository import TagRepository

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get("", response_model=TaxonomyResponse)
async def get_taxonomy(
    repository: TagRepository = Depends(get_repository),
) -> TaxonomyResponse:
    """Get full taxonomy — all categories and tags."""
    categories = await repository.get_all_categories()
    tags = await repository.get_all_active_tags()

    return TaxonomyResponse(
        categories=[
            CategoryResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                is_active=c.is_active,
                sort_order=c.sort_order,
            )
            for c in categories
        ],
        tags=[
            TagResponse(
                id=t.id,
                category_id=t.category_id,
                name=t.name,
                slug=t.slug,
                description=t.description,
                color=t.color,
                icon=t.icon,
                priority=t.priority,
                is_active=t.is_active,
            )
            for t in tags
        ],
        total_categories=len(categories),
        total_tags=len(tags),
    )


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    repository: TagRepository = Depends(get_repository),
) -> list[CategoryResponse]:
    """List all active categories ordered by sort_order."""
    categories = await repository.get_all_categories()
    return [
        CategoryResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            is_active=c.is_active,
            sort_order=c.sort_order,
        )
        for c in categories
    ]


@router.get("/tags", response_model=list[TagResponse])
async def get_tags(
    repository: TagRepository = Depends(get_repository),
) -> list[TagResponse]:
    """List all active tags."""
    tags = await repository.get_all_active_tags()
    return [
        TagResponse(
            id=t.id,
            category_id=t.category_id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            color=t.color,
            icon=t.icon,
            priority=t.priority,
            is_active=t.is_active,
        )
        for t in tags
    ]