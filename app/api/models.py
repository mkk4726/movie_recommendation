"""
Pydantic models for API request/response validation.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


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


class SearchResultMovie(BaseModel):
    """검색 결과 영화 (QuerySearchPipeline 출력용)"""
    movie_id: str = Field(..., description="영화 ID")
    title: str = Field(..., description="영화 제목")
    genres: str = Field(..., description="장르")
    score: float = Field(..., description="검색 관련성 점수")
    overview: Optional[str] = Field(default="", description="영화 줄거리/개요")
    matched_fields: Dict[str, float] = Field(
        default_factory=dict, 
        description="매칭된 필드별 스코어"
    )
    year: Optional[int] = Field(default=None, description="개봉 연도")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": "1",
                "title": "Toy Story",
                "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                "score": 15.42,
                "overview": "Led by Woody, Andy's toys live happily...",
                "matched_fields": {"title": 10.5, "overview": 4.92},
                "year": 1995
            }
        }


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


class QuerySearchResponse(BaseModel):
    """QuerySearchPipeline 검색 결과 응답"""
    query: str = Field(..., description="검색 쿼리")
    total_results: int = Field(..., description="전체 결과 개수")
    results: List[SearchResultMovie] = Field(..., description="검색 결과 리스트")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "toy story animation",
                "total_results": 5,
                "results": [
                    {
                        "movie_id": "1",
                        "title": "Toy Story",
                        "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                        "score": 15.42,
                        "overview": "Led by Woody, Andy's toys live happily...",
                        "matched_fields": {"title": 10.5, "overview": 4.92},
                        "year": 1995
                    }
                ]
            }
        }

