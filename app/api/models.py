"""
Pydantic models for API request/response validation.
"""
from typing import List, Optional
from pydantic import BaseModel


class MovieSummary(BaseModel):
    movie_id: str
    title: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None


class UserRatedMovie(MovieSummary):
    rating: Optional[float] = None


class RecommendedMovie(MovieSummary):
    predicted_rating: Optional[float] = None


class SimilarMovie(MovieSummary):
    similarity: Optional[float] = None


class UserRecommendationResponse(BaseModel):
    user_id: str
    top_watched: List[UserRatedMovie]
    recommendations: List[RecommendedMovie]


class SimilarMoviesResponse(BaseModel):
    movie_id: str
    similar: List[SimilarMovie]


class SearchResponse(BaseModel):
    query: str
    results: List[MovieSummary]

