"""
레거시 Streamlit 데이터 로더 모듈
"""

from .loader import (
    filter_data,
    load_movie_data,
    load_ratings_data,
    search_movies,
)

__all__ = [
    "filter_data",
    "load_movie_data",
    "load_ratings_data",
    "search_movies",
]

