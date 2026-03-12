"""
FastAPI application factory.

Why a factory function (create_app) instead of a module-level app:
  - Tests can create isolated app instances
  - Different configs for test vs production
  - Easier to add middleware and startup events
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tagging.api.routers import health,tagging
from tagging.config import get_settings


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

    return app


# Module-level app instance for uvicorn
app = create_app()