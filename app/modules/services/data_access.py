"""
Utility helpers for loading movie data without relying on Streamlit.
"""
from functools import lru_cache
from typing import Optional, Tuple

import pandas as pd

# Ensure project modules are importable
from modules.core import add_project_paths

add_project_paths()

from data_scraping.common.data_loader import (  # noqa: E402
    load_movie_data as _load_movie_data,
    load_ratings_data as _load_ratings_data,
)
from modeling.utils.data import (  # noqa: E402
    filter_by_min_counts as _filter_by_min_counts,
    search_movies as _search_movies,
)
from modules.config import data_config  # noqa: E402


@lru_cache(maxsize=1)
def load_all_data(
    min_user_ratings: Optional[int] = None,
    min_movie_ratings: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load movie metadata and rating interactions from disk.

    Args:
        min_user_ratings: 최소 사용자 평점 개수 (None이면 config 값 사용)
        min_movie_ratings: 최소 영화 평점 개수 (None이면 config 값 사용)

    Returns:
        Tuple of (movies, ratings, filtered_ratings).
    """
    # config에서 기본값 가져오기
    if min_user_ratings is None:
        min_user_ratings = data_config.min_user_ratings
    if min_movie_ratings is None:
        min_movie_ratings = data_config.min_movie_ratings

    df_movies = _load_movie_data()
    df_ratings = _load_ratings_data()

    try:
        df_filtered = _filter_by_min_counts(
            df_ratings,
            min_user_ratings=min_user_ratings,
            min_movie_ratings=min_movie_ratings,
            verbose=False,
        )
    except ValueError:
        # Filtering can empty the dataset for aggressive thresholds.
        df_filtered = df_ratings.copy()

    return df_movies, df_ratings, df_filtered


def invalidate_data_cache() -> None:
    """Clear cached datasets (useful after refreshing source files)."""
    load_all_data.cache_clear()
    search_movies_cached.cache_clear()


@lru_cache(maxsize=64)
def search_movies_cached(query: str, limit: int = 10) -> pd.DataFrame:
    """
    Search movie titles with simple caching to avoid repeated filtering.
    """
    normalized = (query or "").strip()
    if not normalized:
        return pd.DataFrame()

    df_movies, _, _ = load_all_data()
    result = _search_movies(df_movies, normalized, limit)
    return result.copy()


@lru_cache(maxsize=1)
def get_data_stats() -> dict:
    """
    데이터 통계를 계산하고 캐시합니다.
    
    Returns:
        통계 정보 딕셔너리
    """
    df_movies, df_ratings, _ = load_all_data()
    
    if df_movies is None or df_ratings is None:
        return {
            "total_movies": "0",
            "total_ratings": "0",
            "total_users": "0",
            "avg_rating": None,
        }
    
    return {
        "total_movies": f"{len(df_movies):,}",
        "total_ratings": f"{len(df_ratings):,}",
        "total_users": f"{df_ratings['user_id'].nunique():,}" if "user_id" in df_ratings.columns else "0",
        "avg_rating": float(df_ratings["rating"].mean()) if "rating" in df_ratings.columns else None,
    }

