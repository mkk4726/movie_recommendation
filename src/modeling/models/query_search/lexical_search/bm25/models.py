"""
BM25 데이터 모델

검색 결과 및 데이터 구조 정의
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BM25SearchResult(BaseModel):
    """BM25 검색 결과 (Pydantic 모델)"""
    movie_id: str = Field(..., description="영화 ID")
    score: float = Field(..., description="BM25 스코어")
    title: str = Field(..., description="영화 제목")
    genres: str = Field(..., description="장르")
    matched_fields: Dict[str, float] = Field(
        default_factory=dict,
        description="매칭된 필드별 스코어"
    )
    overview: str = Field(default="", description="영화 줄거리/개요")
    year: Optional[int] = Field(default=None, description="개봉 연도")
    vote_average: Optional[float] = Field(default=None, description="평균 평점")
    vote_count: Optional[int] = Field(default=None, description="평가 수")
    language: Optional[str] = Field(default="", description="영화 언어")
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 형식으로 출력"""
        matched_info = ", ".join([f"{k}: {v:.2f}" for k, v in self.matched_fields.items() if v > 0])
        return f"[{self.score:.2f}] {self.title} ({self.genres}) - {matched_info}"
    
    class Config:
        # 다양한 타입의 movie_id 허용 (int, str 등)
        json_encoders = {
            Any: lambda v: str(v)
        }

