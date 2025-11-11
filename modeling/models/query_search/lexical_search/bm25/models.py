"""
BM25 데이터 모델

검색 결과 및 데이터 구조 정의
"""
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class BM25SearchResult:
    """BM25 검색 결과"""
    movie_id: Any  # 영화 ID (movieId)
    score: float  # BM25 스코어
    title: str  # 영화 제목
    genres: str  # 장르
    matched_fields: Dict[str, float]  # 매칭된 필드별 스코어
    overview: str = ""  # 영화 줄거리/개요
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 형식으로 출력"""
        matched_info = ", ".join([f"{k}: {v:.2f}" for k, v in self.matched_fields.items() if v > 0])
        return f"[{self.score:.2f}] {self.title} ({self.genres}) - {matched_info}"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "movie_id": self.movie_id,
            "score": float(self.score),
            "title": self.title,
            "genres": self.genres,
            "overview": self.overview,
            "matched_fields": {k: float(v) for k, v in self.matched_fields.items()}
        }

