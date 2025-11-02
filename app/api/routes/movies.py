"""
Movie-related API endpoints: search and similar movies.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from modules.services.data_access import load_all_data, search_movies_cached
from modules.services.recommender_service import get_recommender_service
from app.api.models import SearchResponse, SimilarMoviesResponse
from app.api.utils import from_dataframe

router = APIRouter()


@router.get("/movies/search", response_model=SearchResponse)
def search_movies(query: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Search for movies by query string."""
    try:
        df = search_movies_cached(query=query, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    results = from_dataframe(df)
    return SearchResponse(query=query, results=results)


@router.get("/movies/{movie_id}/similar", response_model=SimilarMoviesResponse)
def similar_movies(
    movie_id: str,
    top_n: int = Query(10, ge=1, le=50),
    genre: Optional[List[str]] = Query(None),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, ge=1800),
):
    """Get similar movies for a given movie ID."""
    recommender = get_recommender_service()
    try:
        df_movies, _, _ = load_all_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if movie_id not in df_movies["movie_id"].values:
        raise HTTPException(
            status_code=404,
            detail=f"Movie '{movie_id}' not found in movie catalog.",
        )

    filters = {}
    if genre:
        filters["genre"] = genre
    if min_year is not None:
        filters["min_year"] = min_year
    if max_year is not None:
        filters["max_year"] = max_year

    try:
        similar_df = recommender.similar_movies(
            movie_id=movie_id,
            df_movies=df_movies,
            n_recommendations=top_n,
            filters=filters if filters else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Add similarity column name consistency (already handled in wrapper)
    similar = from_dataframe(similar_df, include_similarity=True)
    return SimilarMoviesResponse(movie_id=movie_id, similar=similar)

