"""
서비스 레이어 초기화 모듈
"""

from .data_service import load_all_data, load_recommender_models
from .recommender import MovieRecommender

__all__ = [
    "load_all_data",
    "load_recommender_models",
    "MovieRecommender",
]
