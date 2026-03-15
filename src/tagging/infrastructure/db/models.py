"""
SQLAlchemy ORM models.

These are separate from domain models intentionally:
  - Domain models: pure Python, no DB knowledge
  - ORM models: know about tables, columns, indexes
  - Repository: translates between the two

Each ORM model has a to_domain() method that converts
a DB row into a clean domain model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.tag import Tag
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag_result import TagResult
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


class Base(DeclarativeBase):
    """
    Shared Base class  for ORM Model.
    All tables are inherit from this
    """

    pass


class TagCategoryModel(Base):
    """
    Maps TagCategory domain model to tag_categories table
    """

    __tablename__ = "tag_categories"
    __table_args__ = (
        Index("ix_tag_categories_is_active", "is_active"),
        Index("ix_tag_categories_sort_order", "sort_order"),
    )
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Relationship — one category has many tags
    tags: Mapped[list["TagModel"]] = relationship(
        "TagModel",
        back_populates="category",
        lazy="selectin",
    )

    def to_domain(self) -> TagCategory:
        """Convert ORM row to domain model."""
        return TagCategory(
            id=self.id,
            name=self.name,
            slug=self.slug,
            description=self.description,
            is_active=self.is_active,
            sort_order=self.sort_order,
        )


class TagModel(Base):
    """
    Maps Tag domain model to tags table.
    """

    __tablename__ = "tags"

    __table_args__ = (
        Index("ix_tags_category_id", "category_id"),
        Index("ix_tags_is_active", "is_active"),
        Index("ix_tags_priority", "priority"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tag_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6B7280")
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="tag")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Relationships
    category: Mapped["TagCategoryModel"] = relationship(
        "TagCategoryModel",
        back_populates="tags",
    )
    rules: Mapped[list["TagRuleModel"]] = relationship(
        "TagRuleModel",
        back_populates="tag",
        lazy="selectin",
    )

    def to_domain(self) -> Tag:
        """Convert ORM row to domain model."""
        return Tag(
            id=self.id,
            category_id=self.category_id,
            name=self.name,
            slug=self.slug,
            description=self.description,
            color=self.color,
            icon=self.icon,
            priority=self.priority,
            is_active=self.is_active,
        )


class TagRuleModel(Base):
    """
    Maps TagRule domain model to tag_rules table.
    """

    __tablename__ = "tag_rules"

    __table_args__ = (
        Index("ix_tag_rules_tag_id", "tag_id"),
        Index("ix_tag_rules_is_enabled", "is_enabled"),
        Index("ix_tag_rules_priority", "priority"),
    )
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Relationships
    tag: Mapped["TagModel"] = relationship(
        "TagModel",
        back_populates="rules",
    )
    conditions: Mapped[list["TagRuleConditionModel"]] = relationship(
        "TagRuleConditionModel",
        back_populates="rule",
        lazy="selectin",
        order_by="TagRuleConditionModel.created_at",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> TagRule:
        """Convert ORM row to domain model including conditions."""
        return TagRule(
            id=self.id,
            tag_id=self.tag_id,
            name=self.name,
            priority=self.priority,
            is_enabled=self.is_enabled,
            conditions=[c.to_domain() for c in self.conditions],
        )


class TagRuleConditionModel(Base):
    """
    Maps TagRuleCondition domain model to tag_rule_conditions table.
    """

    __tablename__ = "tag_rule_conditions"

    __table_args__ = (Index("ix_tag_rule_conditions_rule_id", "rule_id"),)
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    rule_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tag_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)
    values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Relationship
    rule: Mapped["TagRuleModel"] = relationship(
        "TagRuleModel",
        back_populates="conditions",
    )

    def to_domain(self) -> TagRuleCondition:
        """Convert ORM row to domain model."""
        return TagRuleCondition(
            id=self.id,
            condition_type=ConditionType(self.condition_type),
            operator=ConditionOperator(self.operator),
            values=self.values,
        )


class TagResultModel(Base):
    """Persists tag results from the pipeline."""

    __tablename__ = "tag_results"

    __table_args__ = (
        Index("ix_tag_results_note_id", "note_id"),
        Index("ix_tag_results_ro_id", "ro_id"),
        Index("ix_tag_results_shop_id", "shop_id"),
        Index("ix_tag_results_tag_id", "tag_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    note_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ro_id: Mapped[str] = mapped_column(String(36), nullable=False)
    shop_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def to_domain(self, tag: Tag) -> TagResult:
        return TagResult(
            tag=tag,
            confidence=self.confidence,
            source=TagSource(self.source),
            reasoning=self.reasoning,
        )
