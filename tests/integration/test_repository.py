"""
Integration tests for TagRepository.

Uses testcontainers to spin up a real PostgreSQL instance.
No mocking — this verifies the actual SQL queries work.

Run: uv run pytest tests/integration/ -v --no-cov -m integration
Expected: GREEN (requires Docker)
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag_result import TagResult
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition
from tagging.infrastructure.db.models import Base
from tagging.infrastructure.db.repository import TagRepository

# ─────────────────────────────────────────────
# Fixtures — shared test infrastructure
# ─────────────────────────────────────────────


@pytest.fixture(scope="session")
def postgres_container():
    """
    Spin up a real PostgreSQL container for the test session.
    scope="session" means one container for ALL integration tests.
    Destroyed automatically when tests finish.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_container):
    """Create async SQLAlchemy engine connected to test container."""
    # testcontainers returns psycopg2 URL — convert to asyncpg
    url = postgres_container.get_connection_url()
    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Each test gets its own connection with rollback after."""
    async with db_engine.connect() as conn:
        await conn.begin()
        async_session = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session
        await conn.rollback()


@pytest_asyncio.fixture
async def repository(db_session):
    """TagRepository instance with real DB session."""
    return TagRepository(session=db_session)


# ─────────────────────────────────────────────
# Helper fixtures — test data
# ─────────────────────────────────────────────


@pytest_asyncio.fixture
async def sample_category(repository) -> TagCategory:
    return await repository.create_category(
        TagCategory(
            id="cat-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
    )


@pytest_asyncio.fixture
async def sample_tag(repository, sample_category) -> Tag:
    return await repository.create_tag(
        Tag(
            id="tag-1",
            category_id=sample_category.id,
            name="Parts Delay",
            slug="parts-delay",
            description="RO waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
    )


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────


class TestTagRepository:
    pytestmark = [
        pytest.mark.integration,
        pytest.mark.asyncio(loop_scope="session"),
    ]

    async def test_create_and_get_category(self, repository):
        """Can create a category and retrieve it."""
        uid = uuid.uuid4().hex[:8]
        category = await repository.create_category(
            TagCategory(
                id=f"cat-{uid}",
                name="Customer",
                slug=f"customer-{uid}",
                description="Customer issues",
                is_active=True,
                sort_order=2,
            )
        )
        assert category.name == "Customer"

        categories = await repository.get_all_categories()
        slugs = [c.slug for c in categories]
        assert f"customer-{uid}" in slugs

    async def test_get_tags_by_category(self, repository, sample_category, sample_tag):
        """Returns only tags belonging to the given category."""
        tags = await repository.get_tags_by_category(sample_category.id)
        assert len(tags) >= 1
        assert any(t.slug == sample_tag.slug for t in tags)

    async def test_get_all_active_tags(self, repository, sample_category, sample_tag):
        """Returns all active tags."""
        tags = await repository.get_all_active_tags()
        assert len(tags) >= 1
        assert all(t.is_active for t in tags)

    async def test_create_and_get_rule(self, repository, sample_tag):
        """Can create a rule and retrieve it by tag."""
        uid = uuid.uuid4().hex[:8]
        rule = await repository.create_rule(
            TagRule(
                id=f"rule-{uid}",
                tag_id=sample_tag.id,
                name="Parts Delay Detection",
                priority=100,
                is_enabled=True,
                conditions=[
                    TagRuleCondition(
                        id=f"cond-{uid}",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["backordered", "waiting on parts"],
                    )
                ],
            )
        )
        assert rule.name == "Parts Delay Detection"
        rules = await repository.get_rules_for_tag(sample_tag.id)
        assert len(rules) >= 1
        assert rules[0].conditions[0].values == [
            "backordered",
            "waiting on parts",
        ]

    async def test_save_and_retrieve_tag_result(self, repository, sample_tag):
        """Can save a tag result and retrieve it by note_id."""
        uid = uuid.uuid4().hex[:8]
        context = NoteContext(
            note_id=f"note-{uid}",
            ro_id=f"ro-{uid}",
            shop_id=f"shop-{uid}",
            text="waiting on parts from supplier",
            event_type="note",
        )
        result = TagResult(
            tag=sample_tag,
            confidence=1.0,
            source=TagSource.RULES,
            reasoning="matched rule: Parts Delay Detection",
        )

        await repository.save_tag_result(context, result)

        retrieved = await repository.get_results_for_note(f"note-{uid}")
        assert len(retrieved) >= 1
        assert retrieved[0].tag.slug == sample_tag.slug
        assert retrieved[0].confidence == 1.0
        assert retrieved[0].source == TagSource.RULES

    async def test_get_all_rules(self, repository, sample_tag):
        """Can retrieve all rules."""
        await repository.create_rule(
            TagRule(
                id="rule-all-1",
                tag_id=sample_tag.id,
                name="All Rules Test",
                priority=50,
                is_enabled=False,
                conditions=[
                    TagRuleCondition(
                        id="cond-all-1",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["test"],
                    )
                ],
            )
        )
        rules = await repository.get_all_rules()
        assert len(rules) >= 1

    async def test_get_rule_by_id(self, repository, sample_tag):
        """Can retrieve a single rule by ID."""
        await repository.create_rule(
            TagRule(
                id="rule-byid-1",
                tag_id=sample_tag.id,
                name="Get By ID Test",
                priority=50,
                is_enabled=True,
                conditions=[
                    TagRuleCondition(
                        id="cond-byid-1",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["test"],
                    )
                ],
            )
        )
        rule = await repository.get_rule_by_id("rule-byid-1")
        assert rule is not None
        assert rule.name == "Get By ID Test"

    async def test_get_rule_by_id_not_found(self, repository):
        """Returns None when rule not found."""
        rule = await repository.get_rule_by_id("nonexistent")
        assert rule is None

    async def test_delete_rule(self, repository, sample_tag):
        """Can delete a rule."""
        await repository.create_rule(
            TagRule(
                id="rule-del-1",
                tag_id=sample_tag.id,
                name="Delete Test",
                priority=50,
                is_enabled=True,
                conditions=[
                    TagRuleCondition(
                        id="cond-del-1",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["test"],
                    )
                ],
            )
        )
        await repository.delete_rule("rule-del-1")
        rule = await repository.get_rule_by_id("rule-del-1")
        assert rule is None
