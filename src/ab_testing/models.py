"""
추천 평가를 위한 데이터 모델
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MovieRecommendation(BaseModel):
    """영화 추천 아이템"""

    movie_id: str = Field(..., description="영화 ID")
    title: str = Field(..., description="영화 제목")
    year: Optional[int] = Field(default=None, description="개봉 연도")
    genres: Optional[List[str]] = Field(default=None, description="장르")
    description: Optional[str] = Field(default=None, description="영화 설명")
    score: Optional[float] = Field(default=None, description="추천 점수")
    rank: Optional[int] = Field(default=None, description="추천 순위")

    def to_display_text(self, include_description: bool = True) -> str:
        """디스플레이용 텍스트 생성"""
        text = f"{self.title}"

        if self.year:
            text += f" ({self.year})"

        if self.genres:
            text += f" - Genres: {', '.join(self.genres)}"

        if include_description and self.description:
            desc = self.description[:200] + "..." if len(self.description) > 200 else self.description
            text += f"\n  {desc}"

        return text


class RecommendationList(BaseModel):
    """추천 리스트"""

    list_id: str = Field(..., description="리스트 ID (A 또는 B)")
    system_name: str = Field(..., description="추천 시스템 이름")
    recommendations: List[MovieRecommendation] = Field(..., description="추천 영화 리스트")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")

    def to_display_text(self, include_descriptions: bool = True) -> str:
        """디스플레이용 텍스트 생성"""
        text = f"List {self.list_id} ({self.system_name}):\n"

        for i, rec in enumerate(self.recommendations, 1):
            text += f"{i}. {rec.to_display_text(include_descriptions)}\n"

        return text


class EvaluationResult(BaseModel):
    """LLM 평가 결과"""

    preferred_list: Literal["A", "B", "none"] = Field(..., description="선호하는 리스트")
    reasoning: str = Field(..., description="선호 이유")
    click_probability_A: float = Field(..., ge=0.0, le=1.0, description="List A 클릭 확률")
    click_probability_B: float = Field(..., ge=0.0, le=1.0, description="List B 클릭 확률")
    relevance_score_A: Optional[float] = Field(default=None, ge=0, le=10, description="List A 관련성 점수")
    relevance_score_B: Optional[float] = Field(default=None, ge=0, le=10, description="List B 관련성 점수")
    timestamp: datetime = Field(default_factory=datetime.now, description="평가 시각")

    @field_validator("click_probability_A", "click_probability_B")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        """확률 값 검증"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Probability must be between 0 and 1")
        return v


class UserContext(BaseModel):
    """사용자 컨텍스트 (평가 시 참고할 정보)"""

    user_description: str = Field(..., description="사용자 설명 (선호 장르, 분위기 등)")
    additional_context: Optional[Dict[str, Any]] = Field(default=None, description="추가 컨텍스트")

    def to_prompt_text(self) -> str:
        """프롬프트에 사용할 텍스트 생성"""
        text = f"User: {self.user_description}"
        if self.additional_context:
            text += f"\nAdditional Context: {self.additional_context}"
        return text
