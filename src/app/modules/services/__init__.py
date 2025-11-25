"""
서비스 레이어 초기화 모듈 (FastAPI용)
Streamlit 버전은 app/legacy/streamlit/modules/services/에 있습니다.
"""

from .data_access import load_all_data, search_movies_cached, invalidate_data_cache
from .recommender_service import get_recommender_service, RecommenderService

__all__ = [
    "load_all_data",
    "search_movies_cached",
    "invalidate_data_cache",
    "get_recommender_service",
    "RecommenderService",
]
