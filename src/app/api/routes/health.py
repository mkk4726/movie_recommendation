"""
Health check endpoint.
"""

from fastapi import APIRouter, HTTPException
from app.services.recommender_service import get_recommender_service

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict:
    """Liveness probe."""
    try:
        # Touch the recommender lazily to surface model path errors early.
        get_recommender_service()
        return {"status": "ok"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
