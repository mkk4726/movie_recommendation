"""
데이터 로딩 및 전처리 유틸리티 (Streamlit 데코레이터 없는 깔끔한 버전)
데이터 로드 하는 부분만, 전처리 등은 모두 modeling에 하도록
"""
import pandas as pd
from pathlib import Path
from .data_storage import DataStorage


def get_data_path() -> Path:
    """데이터 디렉토리 경로를 반환 (로컬/배포 환경 모두 호환)"""
    # 현재 파일의 위치를 기준으로 프로젝트 루트를 찾음
    current_file = Path(__file__).resolve()
    # data_scraping/common/data_loader.py -> data_scraping/common -> data_scraping -> project_root
    project_root = current_file.parent.parent.parent
    data_dir = project_root / 'data_scraping' / 'data'
    return data_dir


def load_movie_data(data_path: str = None) -> pd.DataFrame:
    """영화 정보 데이터 로딩 (DataStorage.load_movie_info 사용)"""
    if data_path is None:
        data_path = get_data_path()
        
    # DataStorage 인스턴스 생성
    storage = DataStorage()
    storage.config.DATA_DIR = data_path
    
    # DataStorage의 load_movie_info 사용
    df_movies = storage.load_movie_info()
    
    if df_movies.empty:
        return df_movies
    
    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {
        'MovieID': 'movie_id',
        'Title': 'title',
        'Year': 'year',
        'Genre': 'genre',
        'Country': 'country',
        'Runtime': 'runtime',
        'Age': 'age_rating',
        'Cast_Production': 'cast',
        'Synopsis': 'plot',
        'Avg_Rating': 'avg_score',
        'N_Rating': 'popularity',
        'N_Comments': 'review_count'
    }
    
    # 컬럼명 변환
    df_movies = df_movies.rename(columns=column_mapping)
    
    # 기존 로직과 동일한 전처리 수행
    df_movies['avg_score'] = pd.to_numeric(df_movies['avg_score'], errors='coerce')
    df_movies['popularity'] = pd.to_numeric(df_movies['popularity'], errors='coerce')
    df_movies['year'] = pd.to_numeric(df_movies['year'], errors='coerce')
    df_movies = df_movies.dropna(subset=['avg_score'])
    
    return df_movies.reset_index(drop=True, inplace=False)


def load_ratings_data(data_path: str = None) -> pd.DataFrame:
    """사용자 평점 데이터 로딩 (DataStorage.load_custom_rating 사용)"""
    if data_path is None:
        data_path = get_data_path()
        
    # DataStorage 인스턴스 생성
    storage = DataStorage()
    storage.config.DATA_DIR = data_path
    
    # DataStorage의 load_custom_rating 사용
    df_ratings = storage.load_custom_rating()
    
    if df_ratings.empty:
        return df_ratings
    
    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {
        'CustomID': 'user_id',
        'MovieID': 'movie_id',
        'MovieName': 'movie_title',
        'Rating': 'rating'
    }
    
    # 컬럼명 변환
    df_ratings = df_ratings.rename(columns=column_mapping)
    
    # 기존 로직과 동일한 전처리 수행
    df_ratings['rating'] = pd.to_numeric(df_ratings['rating'], errors='coerce')
    df_ratings = df_ratings[(df_ratings['rating'] >= 0) & (df_ratings['rating'] <= 5)]
    df_ratings = df_ratings.dropna(subset=['rating'])
    
    return df_ratings.reset_index(drop=True, inplace=False)




