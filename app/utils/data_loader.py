"""
데이터 로딩 및 전처리 유틸리티
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict
import streamlit as st


def get_data_path() -> Path:
    """데이터 디렉토리 경로를 반환 (로컬/배포 환경 모두 호환)"""
    # 현재 파일의 위치를 기준으로 프로젝트 루트를 찾음
    current_file = Path(__file__).resolve()
    # app/utils/data_loader.py -> app/utils -> app -> project_root
    project_root = current_file.parent.parent.parent
    data_dir = project_root / 'data_scraping' / 'data'
    return data_dir


@st.cache_data
def load_movie_data(data_path: str = None) -> pd.DataFrame:
    """영화 정보 데이터 로딩"""
    movie_info = []
    if data_path is None:
        data_path = get_data_path()
    file_path = Path(data_path) / 'movie_info_watcha.txt'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('/')
            if len(parts) >= 11:
                movie_info.append({
                    'movie_id': parts[0],
                    'title': parts[1],
                    'year': parts[2],
                    'genre': parts[3],
                    'country': parts[4],
                    'runtime': parts[5],
                    'rating': parts[6],
                    'cast': parts[7],
                    'plot': parts[8],
                    'avg_score': parts[9],
                    'popularity': parts[10],
                    'review_count': parts[11] if len(parts) > 11 else None
                })
    
    df_movies = pd.DataFrame(movie_info)
    df_movies['avg_score'] = pd.to_numeric(df_movies['avg_score'], errors='coerce')
    df_movies['popularity'] = pd.to_numeric(df_movies['popularity'], errors='coerce')
    df_movies['year'] = pd.to_numeric(df_movies['year'], errors='coerce')
    df_movies = df_movies.dropna(subset=['avg_score'])
    
    return df_movies


@st.cache_data
def load_ratings_data(data_path: str = None) -> pd.DataFrame:
    """사용자 평점 데이터 로딩"""
    ratings = []
    if data_path is None:
        data_path = get_data_path()
    file_path = Path(data_path) / 'custom_movie_rating.txt'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('/')
            if len(parts) >= 4:
                try:
                    ratings.append({
                        'user_id': parts[0],
                        'movie_id': parts[1],
                        'movie_title': parts[2],
                        'rating': float(parts[3])
                    })
                except ValueError:
                    continue
    
    df_ratings = pd.DataFrame(ratings)
    df_ratings = df_ratings[(df_ratings['rating'] >= 0) & (df_ratings['rating'] <= 5)]
    
    return df_ratings


def filter_data(df: pd.DataFrame, 
                min_user_ratings: int = 30, 
                min_movie_ratings: int = 10) -> pd.DataFrame:
    """Cold start 문제 해결을 위한 데이터 필터링"""
    user_counts = df.groupby('user_id').size()
    movie_counts = df.groupby('movie_id').size()
    
    valid_users = user_counts[user_counts >= min_user_ratings].index
    valid_movies = movie_counts[movie_counts >= min_movie_ratings].index
    
    df_filtered = df[
        (df['user_id'].isin(valid_users)) & 
        (df['movie_id'].isin(valid_movies))
    ].copy()
    
    return df_filtered


def search_movies(df_movies: pd.DataFrame, query: str, limit: int = 10) -> pd.DataFrame:
    """영화 제목으로 검색"""
    result = df_movies[df_movies['title'].str.contains(query, case=False, na=False)]
    return result.head(limit)

