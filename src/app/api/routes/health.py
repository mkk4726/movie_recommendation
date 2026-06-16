"""
Health check endpoint.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
