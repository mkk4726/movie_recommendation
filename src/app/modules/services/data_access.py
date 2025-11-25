"""
Utility helpers for loading movie data without relying on Streamlit.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import yaml

# Ensure project modules are importable
from modules.core import add_project_paths

add_project_paths()

from data_scraping.common.data_loader import (
    load_movie_cast as _load_movie_cast,
)
from data_scraping.common.data_loader import (  # noqa: E402
    load_movie_data as _load_movie_data,
)
from data_scraping.common.data_loader import (
    load_ratings_data as _load_ratings_data,
)
from modeling.utils.data import (  # noqa: E402
    filter_by_min_counts as _filter_by_min_counts,
)
from modeling.utils.data import (
    search_movies as _search_movies,
)


def _load_data_config() -> dict:
    """
    data_config.yaml 파일을 읽어서 설정을 반환합니다.

    Returns:
        data 설정 딕셔너리 (min_user_ratings, min_movie_ratings 포함)
    """
    # 프로젝트 루트 기준으로 data_config.yaml 경로 설정
    # 현재 파일: app/modules/services/data_access.py
    # data_config.yaml: modeling/utils/data_config.yaml
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent  # services -> modules -> app -> project_root
    data_config_path = project_root / "modeling" / "utils" / "data_config.yaml"

    try:
        with open(data_config_path, "r", encoding="utf-8") as f:
            data_config_dict = yaml.safe_load(f)

        # data 섹션 추출
        data_config = data_config_dict.get("data", {})
        return data_config
    except FileNotFoundError:
        # 파일이 없으면 기본값 반환
        return {
            "min_user_ratings": 10,
            "min_movie_ratings": 30,
        }
    except Exception as e:
        # 기타 오류 시 기본값 반환
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"data_config.yaml 로드 실패, 기본값 사용: {e}")
        return {
            "min_user_ratings": 10,
            "min_movie_ratings": 30,
        }


# 데이터 설정 로드 (캐시 적용)
_data_config_cache = None


def get_data_config() -> dict:
    """
    데이터 설정을 반환합니다 (캐시 사용).

    Returns:
        data 설정 딕셔너리
    """
    global _data_config_cache
    if _data_config_cache is None:
        _data_config_cache = _load_data_config()
    return _data_config_cache


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
    data_config = get_data_config()
    if min_user_ratings is None:
        min_user_ratings = data_config.get("min_user_ratings", 10)
    if min_movie_ratings is None:
        min_movie_ratings = data_config.get("min_movie_ratings", 30)

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


@lru_cache(maxsize=1)
def load_cast_data() -> pd.DataFrame:
    """
    Load movie cast and crew data from disk (cached).

    Returns:
        Cast DataFrame with columns: adult, gender, id, known_for_department,
        name, original_name, popularity, profile_path, cast_id, character,
        credit_id, order, tmdb_id, imdb_id
    """
    return _load_movie_cast()


def invalidate_data_cache() -> None:
    """Clear cached datasets (useful after refreshing source files)."""
    load_all_data.cache_clear()
    load_cast_data.cache_clear()
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
