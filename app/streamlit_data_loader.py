"""
Streamlit용 데이터 로더 wrapper
Streamlit 데코레이터를 적용한 버전
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

import streamlit as st
import pandas as pd
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


@st.cache_data(ttl=3600, show_spinner=False)  # 1시간 캐시 유지, 스피너 숨김
def search_movies(df_movies, query: str, limit: int = 10):
    """영화 제목으로 검색 (Streamlit 캐싱 적용, 에러 방지)"""
    try:
        # 쿼리가 비어있거나 None인 경우 빈 DataFrame 반환
        if not query or not query.strip():
            return pd.DataFrame()
        
        # 쿼리 정규화 (공백 제거, 소문자 변환)
        normalized_query = query.strip().lower()
        
        # 검색 실행
        result = _search_movies(df_movies, normalized_query, limit)
        
        # 결과가 비어있으면 빈 DataFrame 반환
        if result is None or result.empty:
            return pd.DataFrame()
            
        return result
        
    except Exception as e:
        # 에러 발생 시 빈 DataFrame 반환 (사용자에게 에러 노출하지 않음)
        print(f"Search error: {e}")  # 디버깅용 로그
        return pd.DataFrame()
