"""
Streamlit용 데이터 로더 wrapper
"""
import pandas as pd
import streamlit as st

# 경로 자동 추가 (core/paths.py가 처리)
from modules.core import add_project_paths  # noqa: E402
add_project_paths()

from data_scraping.common.data_loader import (  # noqa: E402
    load_movie_data as _load_movie_data,
    load_ratings_data as _load_ratings_data,
)
from modeling.utils.data import (  # noqa: E402
    filter_by_min_counts as _filter_by_min_counts,
    search_movies as _search_movies,
)


@st.cache_data
def load_movie_data(data_path: str = None):
    """영화 정보 데이터 로딩 (Streamlit 캐싱 적용)"""
    return _load_movie_data(data_path)


@st.cache_data
def load_ratings_data(data_path: str = None):
    """사용자 평점 데이터 로딩 (Streamlit 캐싱 적용)"""
    return _load_ratings_data(data_path)


def filter_data(df, min_user_ratings: int = 30, min_movie_ratings: int = 10):
    """Cold start 문제 해결을 위한 데이터 필터링"""
    if df is None:
        return pd.DataFrame()
    if df.empty:
        return df.copy()
    return _filter_by_min_counts(df, min_user_ratings, min_movie_ratings)


@st.cache_data(ttl=3600, show_spinner=False)  # 1시간 캐시 유지, 스피너 숨김
def search_movies(df_movies, query: str, limit: int = 10):
    """영화 제목으로 검색 (Streamlit 캐싱 적용, 에러 방지)"""
    try:
        if not query or not query.strip():
            return pd.DataFrame()

        normalized_query = query.strip().lower()
        result = _search_movies(df_movies, normalized_query, limit)
        if result is None or result.empty:
            return pd.DataFrame()

        return result

    except Exception as e:
        print(f"Search error: {e}")  # 디버깅용 로그
        return pd.DataFrame()
