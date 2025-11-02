"""
데이터 로딩 및 전처리 유틸리티 (Streamlit 데코레이터 없는 깔끔한 버전)
데이터 로드 하는 부분만, 전처리 등은 모두 modeling에 하도록

ML-32M 데이터셋을 사용합니다.
"""
import pandas as pd
from pathlib import Path
import re


def _get_year_config():
    """연도 설정 값을 lazy import로 가져오기 (순환 import 방지)"""
    try:
        from app.modules.config import MIN_YEAR, MAX_YEAR
        return MIN_YEAR, MAX_YEAR
    except ImportError:
        # fallback: app 모듈이 없는 경우 기본값 사용
        return 1950, 2026

def get_ml32m_data_path() -> Path:
    """ML-32M 데이터 디렉토리 경로를 반환"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    ml32m_dir = project_root / 'data_scraping' / 'ml-32m'
    return ml32m_dir


def load_movie_data(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 영화 정보 데이터 로딩
    movies.csv 파일을 읽어서 기존 형식과 호환되는 형태로 변환
    
    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)
    
    Returns:
        영화 정보 DataFrame
    """
    if data_path is None:
        ml32m_dir = get_ml32m_data_path()
    else:
        ml32m_dir = Path(data_path)
    
    movies_file = ml32m_dir / 'movies.csv'
    
    if not movies_file.exists():
        raise FileNotFoundError(f"ML-32M movies.csv 파일을 찾을 수 없습니다: {movies_file}")
    
    # CSV 읽기
    df_movies = pd.read_csv(movies_file)
    
    if df_movies.empty:
        return df_movies
    
    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {
        'movieId': 'movie_id',
        'title': 'title',
        'genres': 'genre'
    }
    df_movies = df_movies.rename(columns=column_mapping)
    
    # movie_id를 문자열로 변환
    df_movies['movie_id'] = df_movies['movie_id'].astype(str)
    
    # title에서 연도 추출 (예: "Toy Story (1995)" -> 1995)
    year_pattern = r'\((\d{4})\)'
    df_movies['year'] = df_movies['title'].str.extract(year_pattern).astype(float)
    
    # 장르를 공백으로 구분된 문자열로 변환 (예: "Action|Adventure" -> "Action Adventure")
    df_movies['genre'] = df_movies['genre'].str.replace('|', ' ', regex=False)
    df_movies['genre'] = df_movies['genre'].str.replace('(no genres listed)', '', regex=False)
    df_movies['genre'] = df_movies['genre'].str.strip()
    
    # ML-32M에는 없는 컬럼들에 대해 기본값 설정 (기존 호환성 유지)
    df_movies['country'] = ''  # ML-32M에는 국가 정보 없음
    df_movies['runtime'] = ''  # ML-32M에는 러닝타임 정보 없음
    df_movies['age_rating'] = ''  # ML-32M에는 연령 등급 정보 없음
    df_movies['cast'] = ''  # ML-32M에는 출연진 정보 없음
    df_movies['plot'] = ''  # ML-32M에는 줄거리 정보 없음
    df_movies['avg_score'] = 0.0  # ML-32M에는 평균 평점 정보 없음
    df_movies['popularity'] = 0.0  # ML-32M에는 인기도 정보 없음
    df_movies['review_count'] = 0  # ML-32M에는 리뷰 개수 정보 없음
    
    # 연도 필터링 (lazy import 사용)
    MIN_YEAR, MAX_YEAR = _get_year_config()
    df_movies = df_movies[(df_movies['year'] >= MIN_YEAR) & (df_movies['year'] <= MAX_YEAR)]
    
    # 중복 제거 및 재정렬
    df_movies = df_movies.drop_duplicates(subset=['movie_id'], keep='first').reset_index(drop=True)
    
    return df_movies.reset_index(drop=True, inplace=False)


def load_ratings_data(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 사용자 평점 데이터 로딩
    ratings.csv 파일을 읽어서 기존 형식과 호환되는 형태로 변환
    
    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)
    
    Returns:
        평점 정보 DataFrame
    """
    if data_path is None:
        ml32m_dir = get_ml32m_data_path()
    else:
        ml32m_dir = Path(data_path)
    
    ratings_file = ml32m_dir / 'ratings.csv'
    
    if not ratings_file.exists():
        raise FileNotFoundError(f"ML-32M ratings.csv 파일을 찾을 수 없습니다: {ratings_file}")
    
    # CSV 읽기
    df_ratings = pd.read_csv(ratings_file)
    
    if df_ratings.empty:
        return df_ratings
    
    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {
        'userId': 'user_id',
        'movieId': 'movie_id',
        'rating': 'rating'
    }
    df_ratings = df_ratings.rename(columns=column_mapping)
    
    # user_id와 movie_id를 문자열로 변환
    df_ratings['user_id'] = df_ratings['user_id'].astype(str)
    df_ratings['movie_id'] = df_ratings['movie_id'].astype(str)
    
    # ML-32M 평점은 0.5~5.0 범위이므로 0~5 범위로 유지
    # (기존 코드에서 이미 0~5 범위로 필터링하므로 그대로 사용 가능)
    
    # 필터링: 유효한 평점만 유지
    df_ratings = df_ratings[(df_ratings['rating'] >= 0) & (df_ratings['rating'] <= 5)]
    df_ratings = df_ratings.dropna(subset=['rating'])
    
    return df_ratings.reset_index(drop=True, inplace=False)




