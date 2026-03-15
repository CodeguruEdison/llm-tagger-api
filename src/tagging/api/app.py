"""
FastAPI application factory.

Why a factory function (create_app) instead of a module-level app:
  - Tests can create isolated app instances
  - Different configs for test vs production
  - Easier to add middleware and startup events
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from tagging.api.routers import health, rules, tagging, taxonomy
from tagging.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: log Langfuse status so we can verify tracing from docker logs."""
    import sys

    from tagging.infrastructure.observability import get_langfuse_client

    client = get_langfuse_client()
    msg = (
        "Langfuse tracing ON → %s"
        % (get_settings().langfuse_host or "default")
        if client is not None
        else "Langfuse tracing OFF — set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env (get keys from http://localhost:3001)"
    )
    logger.info(msg)
    # Ensure it shows in docker logs even if logging config suppresses INFO
    print(msg, file=sys.stderr, flush=True)
    yield
    # shutdown: nothing to do


async def integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    """Return 409 Conflict with JSON body for duplicate key / unique violations."""
    msg = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource already exists (duplicate key).", "error": msg},
    )


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Called once at startup.
    """
    settings = get_settings()

    app = FastAPI(
        title="LLM Tagger API",
        description="Intelligent tagging for repair order notes",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(IntegrityError, integrity_error_handler)

    # CORS — allow frontend to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(tagging.router)
    app.include_router(taxonomy.router)
    app.include_router(rules.router)

    return app


# Module-level app instance for uvicorn
app = create_app()
