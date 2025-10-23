"""
Streamlit용 데이터 로더 wrapper
Streamlit 데코레이터를 적용한 버전
"""
import streamlit as st
from data_scraping.common.data_loader import (
    load_movie_data as _load_movie_data,
    load_ratings_data as _load_ratings_data
)
from modeling.utils.data import (
    filter_by_min_counts as _filter_by_min_counts,
    search_movies as _search_movies
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
    return _filter_by_min_counts(df, min_user_ratings, min_movie_ratings)


def search_movies(df_movies, query: str, limit: int = 10):
    """영화 제목으로 검색"""
    return _search_movies(df_movies, query, limit)
