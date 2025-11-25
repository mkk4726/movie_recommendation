"""
Pydantic models for API request/response validation.
"""

from typing import Dict, List, Optional

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
                "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg",
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
                        "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg",
                    }
                ],
                "directors": [
                    {
                        "name": "존 래시터",
                        "original_name": "John Lasseter",
                        "character": None,
                        "profile_path": "/7EdqiNbr4FRjIhKHyPPdFfEEEFG.jpg",
                    }
                ],
                "writers": [],
            }
        }


class SearchResultMovie(BaseModel):
    """검색 결과 영화 (QuerySearchPipeline 출력용)"""

    movie_id: str = Field(..., description="영화 ID")
    title: str = Field(..., description="영화 제목")
    genres: str = Field(..., description="장르")
    score: float = Field(..., description="검색 관련성 점수")
    overview: Optional[str] = Field(default="", description="영화 줄거리/개요")
    matched_fields: Dict[str, float] = Field(default_factory=dict, description="매칭된 필드별 스코어")
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
                            "profile_path": "/eKF1sGJRrZJbfBG1KirPt1cfNd3.jpg",
                        }
                    ],
                    "directors": [],
                    "writers": [],
                },
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
    session_id: Optional[str] = Field(default=None, description="검색 세션 ID (클릭 추적용)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "toy story animation",
                "total_results": 5,
                "session_id": "abc123-def456",
                "results": [
                    {
                        "movie_id": "1",
                        "title": "Toy Story",
                        "genres": "Adventure|Animation|Children|Comedy|Fantasy",
                        "score": 15.42,
                        "overview": "Led by Woody, Andy's toys live happily...",
                        "matched_fields": {"title": 10.5, "overview": 4.92},
                        "year": 1995,
                    }
                ],
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
    # 추가 메타데이터
    imdb_id: Optional[str] = Field(default=None, description="IMDB ID")
    release_date: Optional[str] = Field(default=None, description="개봉일")
    vote_average: Optional[float] = Field(default=None, description="평균 평점")
    vote_count: Optional[int] = Field(default=None, description="평점 개수")
    adult: Optional[bool] = Field(default=None, description="성인 영화 여부")
    language: Optional[str] = Field(default=None, description="언어")

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
                "cast_info": None,
            }
        }


class PosterSearchResponse(BaseModel):
    """포스터 검색 결과 응답"""

    query: str = Field(..., description="검색 쿼리")
    query_type: str = Field(..., description="쿼리 유형 (text/image)")
    total_results: int = Field(..., description="전체 결과 개수")
    results: List[PosterSearchResultMovie] = Field(..., description="검색 결과 리스트")
    session_id: Optional[str] = Field(default=None, description="검색 세션 ID (클릭 추적용)")

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
                        "poster_url": "https://image.tmdb.org/t/p/w500/uXDfjJbdP4ijW5hWSBrPrlKpxab.jpg",
                    }
                ],
            }
        }


# Activity logging models
class ClickEventRequest(BaseModel):
    """클릭 이벤트 요청"""

    session_id: str = Field(..., description="검색 세션 ID")
    movie_id: str = Field(..., description="클릭한 영화 ID")
    position: int = Field(..., ge=0, description="검색 결과 내 순위 (0-indexed)")
    search_query: Optional[str] = Field(default=None, description="검색 쿼리 (참조용)")
    link_type: Optional[str] = Field(default=None, description="링크 타입 (imdb, google_search 등)")


class CTRDataPoint(BaseModel):
    """CTR 분석용 데이터 포인트"""

    session_id: str = Field(..., description="검색 세션 ID")
    ip: str = Field(..., description="사용자 IP")
    search_query: Optional[str] = Field(default=None, description="검색 쿼리")
    search_type: Optional[str] = Field(default=None, description="검색 유형")
    search_timestamp: str = Field(..., description="검색 시각")
    search_results: List[str] = Field(..., description="검색 결과 영화 ID 리스트")
    clicked_movie_id: Optional[str] = Field(default=None, description="클릭한 영화 ID")
    click_position: Optional[int] = Field(default=None, description="클릭 위치")
    click_timestamp: Optional[str] = Field(default=None, description="클릭 시각")


class ActivityStats(BaseModel):
    """활동 통계"""

    total_searches: int = Field(..., description="총 검색 수")
    total_clicks: int = Field(..., description="총 클릭 수")
    total_ratings: int = Field(..., description="총 평점 수")
    total_views: int = Field(..., description="총 조회 수")
    ctr: float = Field(..., description="클릭률 (CTR)")
