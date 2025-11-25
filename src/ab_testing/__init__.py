"""
LLM 기반 추천 평가 모듈

추천 결과를 LLM으로 평가하고 클릭 여부를 예측합니다.
"""

from .llm import LLMEvaluator
from .models import (
    EvaluationResult,
    MovieRecommendation,
    RecommendationList,
    UserContext,
)

__all__ = [
    "LLMEvaluator",
    "MovieRecommendation",
    "RecommendationList",
    "EvaluationResult",
    "UserContext",
]
