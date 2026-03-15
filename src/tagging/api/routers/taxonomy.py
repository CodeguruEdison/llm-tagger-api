"""
Taxonomy router.

GET /taxonomy              ← all categories + tags
GET /taxonomy/categories   ← list categories
GET /taxonomy/tags         ← list all tags
"""
import uuid

from fastapi import APIRouter, Depends, status

from tagging.api.dependencies import get_repository
from tagging.api.schemas import (
    CategoryResponse,
    CreateCategoryRequest,
    CreateTagRequest,
    TagResponse,
    TaxonomyResponse,
)
from tagging.domain.tag import Tag
from tagging.domain.tag_category import TagCategory
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
@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    request: CreateCategoryRequest,
    repository: TagRepository = Depends(get_repository),
) -> CategoryResponse:
    """Create a new tag category."""
    category = TagCategory(
        id=str(uuid.uuid4()),
        name=request.name,
        slug=request.slug,
        description=request.description,
        is_active=request.is_active,
        sort_order=request.sort_order,
    )
    created = await repository.create_category(category)
    return CategoryResponse(
        id=created.id,
        name=created.name,
        slug=created.slug,
        description=created.description,
        is_active=created.is_active,
        sort_order=created.sort_order,
    )
@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    request: CreateTagRequest,
    repository: TagRepository = Depends(get_repository),
) -> TagResponse:
    """Create a new tag."""
    tag = Tag(
        id=str(uuid.uuid4()),
        category_id=request.category_id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        color=request.color,
        icon=request.icon,
        priority=request.priority,
        is_active=request.is_active,
    )
    created = await repository.create_tag(tag)
    return TagResponse(
        id=created.id,
        category_id=created.category_id,
        name=created.name,
        slug=created.slug,
        description=created.description,
        color=created.color,
        icon=created.icon,
        priority=created.priority,
        is_active=created.is_active,
    )
