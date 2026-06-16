"""
영화 검색 및 유사 영화 API.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from app.services.data_access import load_cast_data, search_movies_cached
from app.services.recommender_service import get_item_cf_pipeline

from app.api.schemas import SearchResponse, SimilarMoviesResponse
from app.api.utils import from_dataframe

router = APIRouter()


@router.get("/movies/search", response_model=SearchResponse)
def search_movies(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
    min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점"),
    min_vote_count: int = Query(0, ge=0, description="최소 평가 수"),
):
    """Search for movies by query string."""
    try:
        df = search_movies_cached(query=query, limit=limit)
        if "vote_average" in df.columns:
            df = df[df["vote_average"] >= min_rating]
        if "vote_count" in df.columns:
            df = df[df["vote_count"] >= min_vote_count]
        cast_df = load_cast_data() if include_cast else None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    results = from_dataframe(df, cast_df=cast_df)
    return SearchResponse(query=query, results=results)


@router.get("/movies/{movie_id}/similar", response_model=SimilarMoviesResponse)
def similar_movies(
    movie_id: str,
    top_n: int = Query(10, ge=1, le=50),
    genre: Optional[List[str]] = Query(None),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, ge=1800),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
):
    """Get similar movies for a given movie ID."""
    try:
        cast_df = load_cast_data() if include_cast else None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filters = {}
    if genre:
        filters["genre"] = genre
    if min_year is not None:
        filters["min_year"] = min_year
    if max_year is not None:
        filters["max_year"] = max_year

    try:
        pipeline = get_item_cf_pipeline()
        similar_df = pipeline.search(
            movie_id=movie_id,
            top_n=top_n,
            filters=filters or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if similar_df.empty:
        raise HTTPException(status_code=404, detail=f"Movie '{movie_id}' not found or no similar movies.")

    similar = from_dataframe(similar_df, include_similarity=True, cast_df=cast_df)
    return SimilarMoviesResponse(movie_id=movie_id, similar=similar)
