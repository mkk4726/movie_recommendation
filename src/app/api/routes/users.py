"""
User recommendation API endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.data_access import load_movie_data, load_cast_data, user_exists
from app.services.recommender_service import recommend_for_user as recommend_for_user_func

from app.api.schemas import UserRecommendationResponse
from app.api.utils import from_dataframe

router = APIRouter()


@router.get("/users/{user_id}/recommendations", response_model=UserRecommendationResponse)
def recommend_for_user(
    user_id: str,
    top_n: int = Query(10, ge=1, le=50),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
):
    """Get movie recommendations for a specific user."""
    try:
        df_movies = load_movie_data()
        cast_df = load_cast_data() if include_cast else None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User '{user_id}' not found in ratings dataset.",
        )

    try:
        top_watched_df, recommendations_df = recommend_for_user_func(
            user_id=user_id,
            df_movies=df_movies,
            n=top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    top_watched = from_dataframe(top_watched_df, include_rating=True, cast_df=cast_df)
    recommendations = from_dataframe(recommendations_df, include_predicted=True, cast_df=cast_df)

    return UserRecommendationResponse(
        user_id=user_id,
        top_watched=top_watched,
        recommendations=recommendations,
    )
