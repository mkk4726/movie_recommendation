"""
데이터 접근 레이어 초기화
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
