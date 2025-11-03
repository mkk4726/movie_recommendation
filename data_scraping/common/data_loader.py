"""
영화 데이터 로딩 유틸리티
ML-32M, TMDB 데이터를 통합하여 로드합니다.
"""
import pandas as pd
from data_scraping.common import (
    load_movie_data_ml,
    load_links_data_ml,
    load_ratings_data_ml,
    load_tmdb_data,
)


def load_movie_data() -> pd.DataFrame:
    """
    ML-32M 영화 데이터와 TMDB 메타데이터를 통합하여 로드
    
    Returns:
        통합된 영화 데이터 DataFrame
        컬럼: movie_id, title, genres, imdb_id, tmdb_id, 그리고 TMDB 메타데이터
    """
    # ML-32M 데이터 로드
    df_movies = load_movie_data_ml()
    df_links = load_links_data_ml()
    
    # TMDB 데이터 로드
    df_tmdb = load_tmdb_data()
    
    # ML-32M 데이터 병합 (movie_id 기준)
    df = pd.merge(df_movies, df_links, on='movie_id', how='inner')
    
    # TMDB 데이터 병합 (imdb_id 기준, right join으로 TMDB에 있는 것만 유지)
    df = pd.merge(
        df,
        df_tmdb,
        on='imdb_id',
        how='right',
        suffixes=('', '_tmdb')
    ).reset_index(drop=True)
    
    return df


def load_ratings_data(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 사용자 평점 데이터 로딩
    
    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)
    
    Returns:
        평점 정보 DataFrame
    """
    df_ratings = load_ratings_data_ml(data_path)
    df_movies = load_movie_data()
    
    # set을 사용하여 isin() 연산 성능 개선 (특히 큰 데이터셋에서 유용)
    valid_movie_ids = set(df_movies['movie_id'])
    df_ratings = df_ratings[df_ratings['movie_id'].isin(valid_movie_ids)].reset_index(drop=True)
    
    # apply 대신 pd.to_datetime 사용 (더 효율적)
    df_ratings['time'] = pd.to_datetime(df_ratings['timestamp'], unit='s')
    
    return df_ratings