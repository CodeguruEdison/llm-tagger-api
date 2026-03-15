"""
FastAPI dependencies — injected into route handlers.

Why dependencies:
  - Single place to create DB sessions, repositories, orchestrators
  - Easy to override in tests
  - Automatically closed/cleaned up after each request
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tagging.application.orchestrator import Orchestrator
from tagging.config import get_settings, Settings
from tagging.infrastructure.db.repository import TagRepository
from tagging.infrastructure.llm.chain import LLMChain
from tagging.infrastructure.llm.factory import LLMFactory


def get_settings_dep() -> Settings:
    return get_settings()


async def get_db_session(
    settings: Settings = Depends(get_settings_dep),
) -> AsyncGenerator[AsyncSession, None]:
    """Create a DB session for the request, close after."""
    # Prefer direct Postgres URL when set (avoids pgBouncer auth issues with asyncpg)
    url = settings.direct_database_url or settings.database_url
    engine = create_async_engine(url)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        await session.commit()


async def get_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TagRepository:
    """Create a repository for the request."""
    return TagRepository(session=session)


async def get_orchestrator(
    settings: Settings = Depends(get_settings_dep),
    repository: TagRepository = Depends(get_repository),
) -> Orchestrator:
    """
    Create an orchestrator for the request.
    Wires together repository + LLM chain based on settings.
    Langfuse callback handler is injected when configured so all LLM and
    pipeline runs are traced in one place.
    """
    from tagging.domain.enums.tagging_mode import TaggingMode
    from tagging.infrastructure.observability import get_langfuse_client

    llm_chain = None
    if settings.tagging_mode != TaggingMode.RULES_ONLY:
        factory = LLMFactory.from_settings(settings)
        llm = factory.create()
        llm_chain = LLMChain(llm=llm)

    return Orchestrator(
        repository=repository,
        tagging_mode=settings.tagging_mode,
        llm_confidence_threshold=settings.llm_confidence_threshold,
        llm_chain=llm_chain,
        langfuse_client=get_langfuse_client(),
    )