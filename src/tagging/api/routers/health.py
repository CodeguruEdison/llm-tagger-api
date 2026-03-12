"""
Health check router.

GET /health — is the service alive?
Used by Docker, Kubernetes, and load balancers
to know if the service is ready to receive traffic.
"""
from fastapi import APIRouter
from tagging.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Returns service health status.
    If this endpoint responds, the service is alive.
    """
    return HealthResponse(status="ok")