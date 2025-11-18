"""
Pydantic models for API request/response validation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MovieSummary(BaseModel):
    movie_id: str
    title: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    cast_info: Optional["MovieCastInfo"] = None


class UserRatedMovie(MovieSummary):
    rating: Optional[float] = None


class RecommendedMovie(MovieSummary):
    predicted_rating: Optional[float] = None


class SimilarMovie(MovieSummary):
    similarity: Optional[float] = None


class CastMember(BaseModel):
    """출연진/제작진 정보"""
    name: str = Field(..., description="이름")
    original_name: str = Field(..., description="원어 이름")
    character: Optional[str] = Field(default=None, description="배역/역할")
    profile_path: Optional[str] = Field(default=None, description="프로필 이미지 경로")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "톰 행크스",
                "original_name": "Tom Hanks",
                "character": "Woody (voice)",
                "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg"
            }
        }


class MovieCastInfo(BaseModel):
    """영화 출연진 및 제작진 정보"""
    actors: List[CastMember] = Field(default_factory=list, description="주연 배우 (최대 5명)")
    directors: List[CastMember] = Field(default_factory=list, description="감독")
    writers: List[CastMember] = Field(default_factory=list, description="작가")
    
    class Config:
        json_schema_extra = {
            "example": {
                "actors": [
                    {
                        "name": "톰 행크스",
                        "original_name": "Tom Hanks",
                        "character": "Woody (voice)",
                        "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg"
                    }
                ],
                "directors": [
                    {
                        "name": "존 래시터",
                        "original_name": "John Lasseter",
                        "character": None,
                        "profile_path": "/7EdqiNbr4FRjIhKHyPPdFfEEEFG.jpg"
                    }
                ],
                "writers": []
            }
        }


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
    cast_info: Optional[MovieCastInfo] = Field(default=None, description="출연진 및 제작진 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": "1",
                "title": "Toy Story",
                "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                "score": 15.42,
                "overview": "Led by Woody, Andy's toys live happily...",
                "matched_fields": {"title": 10.5, "overview": 4.92},
                "year": 1995,
                "cast_info": {
                    "actors": [
                        {
                            "name": "톰 행크스",
                            "original_name": "Tom Hanks",
                            "character": "Woody (voice)",
                            "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg"
                        }
                    ],
                    "directors": [],
                    "writers": []
                }
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


class PosterSearchResultMovie(BaseModel):
    """포스터 검색 결과 영화"""
    movie_id: str = Field(..., description="영화 ID")
    score: float = Field(..., description="유사도 점수 (코사인 유사도)")
    title: Optional[str] = Field(default=None, description="영화 제목")
    genres: Optional[str] = Field(default=None, description="장르")
    year: Optional[int] = Field(default=None, description="개봉 연도")
    overview: Optional[str] = Field(default=None, description="영화 줄거리/개요")
    poster_url: Optional[str] = Field(default=None, description="포스터 이미지 URL")
    cast_info: Optional[MovieCastInfo] = Field(default=None, description="출연진 및 제작진 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": "1",
                "score": 0.92,
                "title": "Toy Story",
                "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                "year": 1995,
                "overview": "Led by Woody, Andy's toys live happily...",
                "poster_url": "https://image.tmdb.org/t/p/w500/uXDfjJbdP4ijW5hWSBrPrlKpxab.jpg",
                "cast_info": None
            }
        }


class PosterSearchResponse(BaseModel):
    """포스터 검색 결과 응답"""
    query_type: str = Field(..., description="검색 타입 (text 또는 image)")
    query: Optional[str] = Field(default=None, description="검색 쿼리 (텍스트인 경우)")
    total_results: int = Field(..., description="전체 결과 개수")
    results: List[PosterSearchResultMovie] = Field(..., description="검색 결과 리스트")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_type": "text",
                "query": "action movie with explosions",
                "total_results": 10,
                "results": [
                    {
                        "movie_id": "1",
                        "score": 0.92,
                        "title": "Toy Story",
                        "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                        "year": 1995,
                        "overview": "Led by Woody, Andy's toys live happily...",
                        "poster_url": "https://image.tmdb.org/t/p/w500/uXDfjJbdP4ijW5hWSBrPrlKpxab.jpg"
                    }
                ]
            }
        }

