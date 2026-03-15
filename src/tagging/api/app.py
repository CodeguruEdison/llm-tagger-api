"""
FastAPI application factory.

Why a factory function (create_app) instead of a module-level app:
  - Tests can create isolated app instances
  - Different configs for test vs production
  - Easier to add middleware and startup events
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from tagging.api.routers import health, rules, tagging, taxonomy
from tagging.config import get_settings


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