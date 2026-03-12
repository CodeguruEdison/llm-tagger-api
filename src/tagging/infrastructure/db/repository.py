"""
TagRepository — real PostgreSQL implementation of ITagRepository.

Uses SQLAlchemy async session for all DB operations.
Converts ORM models to domain models via to_domain().
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tagging.application.interfaces import ITagRepository
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag import Tag
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_result import TagResult
from tagging.domain.note_context import NoteContext
from tagging.infrastructure.db.models import (
    TagCategoryModel,
    TagModel,
    TagRuleModel,
    TagRuleConditionModel,
)


class TagRepository(ITagRepository):
    """
    Real DB implementation using SQLAlchemy async.
    Injected into the orchestrator in production.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_categories(self) -> list[TagCategory]:
        result = await self._session.execute(
            select(TagCategoryModel)
            .where(TagCategoryModel.is_active == True)
            .order_by(TagCategoryModel.sort_order)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_tags_by_category(
        self, category_id: str
    ) -> list[Tag]:
        result = await self._session.execute(
            select(TagModel)
            .where(
                TagModel.category_id == category_id,
                TagModel.is_active == True,
            )
            .order_by(TagModel.priority)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_all_active_tags(self) -> list[Tag]:
        result = await self._session.execute(
            select(TagModel)
            .where(TagModel.is_active == True)
            .order_by(TagModel.priority)
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_rules_for_tag(
        self, tag_id: str
    ) -> list[TagRule]:
        result = await self._session.execute(
            select(TagRuleModel)
            .where(
                TagRuleModel.tag_id == tag_id,
                TagRuleModel.is_enabled == True,
            )
            .order_by(TagRuleModel.priority.desc())
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_all_active_rules(self) -> list[TagRule]:
        result = await self._session.execute(
            select(TagRuleModel)
            .where(TagRuleModel.is_enabled == True)
            .order_by(TagRuleModel.priority.desc())
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def save_tag_result(
        self,
        context: NoteContext,
        result: TagResult,
    ) -> None:
        """
        Persist a tag result.
        We store the key fields needed for the UI and reporting.
        """
        from tagging.infrastructure.db.models import TagResultModel
        orm = TagResultModel(
            note_id=context.note_id,
            ro_id=context.ro_id,
            shop_id=context.shop_id,
            tag_id=result.tag.id,
            confidence=result.confidence,
            source=result.source.value,
            reasoning=result.reasoning,
        )
        self._session.add(orm)
        await self._session.flush()

    async def get_results_for_note(
        self, note_id: str
    ) -> list[TagResult]:
        from tagging.infrastructure.db.models import TagResultModel
        result = await self._session.execute(
            select(TagResultModel)
            .where(TagResultModel.note_id == note_id)
        )
        rows = result.scalars().all()
        results = []
        for row in rows:
            tag_result = await self._session.get(TagModel, row.tag_id)
            if tag_result:
                results.append(row.to_domain(tag_result.to_domain()))
        return results

    async def create_category(
        self, category: TagCategory
    ) -> TagCategory:
        """Create a new category. Used in tests and API."""
        orm = TagCategoryModel(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            is_active=category.is_active,
            sort_order=category.sort_order,
        )
        self._session.add(orm)
        await self._session.flush()
        return category

    async def create_tag(self, tag: Tag) -> Tag:
        """Create a new tag. Used in tests and API."""
        orm = TagModel(
            id=tag.id,
            category_id=tag.category_id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description,
            color=tag.color,
            icon=tag.icon,
            priority=tag.priority,
            is_active=tag.is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        return tag

    async def create_rule(self, rule: TagRule) -> TagRule:
        """Create a new rule with conditions. Used in tests and API."""
        orm = TagRuleModel(
            id=rule.id,
            tag_id=rule.tag_id,
            name=rule.name,
            priority=rule.priority,
            is_enabled=rule.is_enabled,
        )
        self._session.add(orm)
        await self._session.flush()

        for condition in rule.conditions:
            cond_orm = TagRuleConditionModel(
                id=condition.id,
                rule_id=rule.id,
                condition_type=condition.condition_type.value,
                operator=condition.operator.value,
                values=condition.values,
            )
            self._session.add(cond_orm)

        await self._session.flush()
        return rule
    async def get_all_rules(self) -> list[TagRule]:
        """Get all rules regardless of enabled status."""
        result = await self._session.execute(
            select(TagRuleModel)
            .order_by(TagRuleModel.priority.desc())
        )
        return [row.to_domain() for row in result.scalars().all()]

    async def get_rule_by_id(
        self, rule_id: str
    ) -> TagRule | None:
        """Get a single rule by ID. Returns None if not found."""
        result = await self._session.get(TagRuleModel, rule_id)
        if not result:
            return None
        return result.to_domain()

    async def update_rule(self, rule: TagRule) -> TagRule:
        """
        Update an existing rule and replace all its conditions.

        Why replace all conditions:
          Simpler than diffing old vs new conditions.
          Conditions cascade delete — clean slate on every update.
        """
        orm = await self._session.get(TagRuleModel, rule.id)
        if not orm:
            raise ValueError(f"Rule not found: {rule.id}")

        # Update rule fields
        orm.name = rule.name
        orm.priority = rule.priority
        orm.is_enabled = rule.is_enabled

        # Delete existing conditions (CASCADE would handle this
        # but we do it explicitly for clarity)
        for condition in orm.conditions:
            await self._session.delete(condition)
        await self._session.flush()

        # Add new conditions
        for condition in rule.conditions:
            cond_orm = TagRuleConditionModel(
                id=condition.id,
                rule_id=rule.id,
                condition_type=condition.condition_type.value,
                operator=condition.operator.value,
                values=condition.values,
            )
            self._session.add(cond_orm)

        await self._session.flush()
        return rule

    async def delete_rule(self, rule_id: str) -> None:
        """Delete a rule — conditions cascade automatically."""
        orm = await self._session.get(TagRuleModel, rule_id)
        if not orm:
            raise ValueError(f"Rule not found: {rule_id}")
        await self._session.delete(orm)
        await self._session.flush()