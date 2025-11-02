"""
User recommendation API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query

from modules.services.data_access import load_all_data
from modules.services.recommender_service import get_recommender_service
from app.api.models import UserRecommendationResponse
from app.api.utils import from_dataframe

router = APIRouter()


@router.get("/users/{user_id}/recommendations", response_model=UserRecommendationResponse)
def recommend_for_user(
    user_id: str,
    top_n: int = Query(10, ge=1, le=50),
):
    """Get movie recommendations for a specific user."""
    recommender = get_recommender_service()
    try:
        df_movies, df_ratings, _ = load_all_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if user_id not in df_ratings["user_id"].values:
        raise HTTPException(
            status_code=404,
            detail=f"User '{user_id}' not found in ratings dataset.",
        )

    try:
        top_watched_df, recommendations_df = recommender.recommend_for_user(
            user_id=user_id,
            df_movies=df_movies,
            n=top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    top_watched = from_dataframe(top_watched_df, include_rating=True)
    recommendations = from_dataframe(recommendations_df, include_predicted=True)

    return UserRecommendationResponse(
        user_id=user_id,
        top_watched=top_watched,
        recommendations=recommendations,
    )

