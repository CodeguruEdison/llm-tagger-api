"""
Abstract interfaces (ports) for the application layer.

Why interfaces:
  - Tests inject MockTagRepository (fast, no Docker)
  - Production injects PostgresTagRepository (real DB)
  - Orchestrator never knows which one it gets
  - Swap DB implementation without touching business logic

This is the Dependency Injection pattern.
"""

from abc import ABC,abstractmethod

from tagging.domain.tag_category import TagCategory
from tagging.domain.tag import Tag
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_result import TagResult
from tagging.domain.note_context import NoteContext

class ITagRepository(ABC):
    """
    Contract for all tag data access.
    Any class that implements this can be used
    anywhere in the application.
    """
    @abstractmethod
    async def get_all_categories(self)->list[TagCategory]:
        """Get all active categories ordered by sort_order."""
        raise NotImplementedError
    @abstractmethod
    async def get_tags_by_category(self,category_id:str)->list[Tag]:
        """Get all active tags for a category."""
        raise NotImplementedError
    @abstractmethod
    async def get_all_active_tags(self) -> list[Tag]:
        """
        Get all active tags across all categories.
        Used by LLM chain to build taxonomy context.
        """
        raise NotImplementedError
    @abstractmethod
    async def get_rules_for_tag(
        self, tag_id: str
    ) -> list[TagRule]:
        """
        Get all enabled rules for a tag ordered by priority.
        Used by rules engine to evaluate conditions.
        """
        raise NotImplementedError
    @abstractmethod
    async def get_all_active_rules(self) -> list[TagRule]:
        """
        Get all enabled rules across all tags.
        Loaded once at startup, cached in Redis.
        """
        raise NotImplementedError
    @abstractmethod
    async def save_tag_result(
        self,
        context: NoteContext,
        result: TagResult,
    ) -> None:
        """
        Persist a tag result after pipeline completes.
        Called once per tag per note.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_results_for_note(
        self, note_id: str
    ) -> list[TagResult]:
        """
        Get all tag results for a note.
        Used by API to return current tags on a note.
        """
        raise NotImplementedError
    