"""
레거시 Streamlit 서비스 모듈
"""

from .data_service import load_all_data, load_recommender_models
from .recommender import MovieRecommender

__all__ = [
    "load_all_data",
    "load_recommender_models",
    "MovieRecommender",
]
