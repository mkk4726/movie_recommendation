from typing import Dict, Tuple, Optional
from dataclasses import dataclass

import pandas as pd


@dataclass
class IDMapping:
    """ID 매핑 정보를 담는 데이터 클래스"""
    user_to_idx: Dict[str, int]
    idx_to_user: Dict[int, str]
    movie_to_idx: Dict[str, int]
    idx_to_movie: Dict[int, str]


def filter_by_min_counts(
    df: pd.DataFrame,
    min_user_ratings: int = 30,
    min_movie_ratings: int = 10,
    verbose: bool = True
) -> pd.DataFrame:
    """
    지정한 기준 이상 평점을 가진 user/movie만 남도록 데이터프레임 필터링
    
    Args:
        df: 평점 데이터프레임 (user_id, movie_id 컬럼 필수)
        min_user_ratings: 사용자가 최소 남겨야 하는 평점 개수
        min_movie_ratings: 영화가 최소 받아야 하는 평점 개수
        verbose: 각 단계별 개수 출력 여부
        
    Returns:
        필터링된 데이터프레임
        
    Raises:
        ValueError: 필수 컬럼이 없거나 빈 데이터프레임일 경우
    """
    if df.empty:
        raise ValueError("빈 데이터프레임은 필터링할 수 없습니다.")
    
    required_columns = {'user_id', 'movie_id'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    
    user_counts = df.groupby('user_id').size()
    movie_counts = df.groupby('movie_id').size()
    
    if verbose:
        print(f"\n[필터링 전] 사용자 수: {len(user_counts):,}명, 영화 수: {len(movie_counts):,}개")

    valid_users = user_counts[user_counts >= min_user_ratings].index
    valid_movies = movie_counts[movie_counts >= min_movie_ratings].index
    
    if verbose:
        print(f"[필터 적용] min_user_ratings: {min_user_ratings}, min_movie_ratings: {min_movie_ratings}")
        print(f"조건 통과 사용자 수: {len(valid_users):,}명, 조건 통과 영화 수: {len(valid_movies):,}개")
    
    df_filtered = df[
        (df['user_id'].isin(valid_users)) & 
        (df['movie_id'].isin(valid_movies))
    ].copy()
    
    if df_filtered.empty:
        raise ValueError("필터링 후 데이터가 비어있습니다. 필터 조건을 완화하세요.")
    
    if verbose:
        filtered_user_counts = df_filtered.groupby('user_id').size()
        filtered_movie_counts = df_filtered.groupby('movie_id').size()
        print(f"[필터링 후] 사용자 수: {len(filtered_user_counts):,}명, 영화 수: {len(filtered_movie_counts):,}개")
        print(f"필터링된 평점 수: {len(df_filtered):,}개 (제거: {len(df) - len(df_filtered):,}개)")
    
    return df_filtered


def preprocess_id_mapping(
    df: pd.DataFrame,
    verbose: bool = True
) -> Tuple[pd.DataFrame, IDMapping]:
    """
    User ID와 Movie ID를 숫자 인덱스로 매핑하는 전처리 함수
    
    Args:
        df: 평점 데이터프레임 (user_id, movie_id 컬럼 필수)
        verbose: 매핑 정보 출력 여부
        
    Returns:
        Tuple[pd.DataFrame, IDMapping]:
            - df_new: user_idx, movie_idx 컬럼이 추가된 데이터프레임
            - id_mapping: ID 매핑 정보를 담은 IDMapping 객체
            
    Raises:
        ValueError: 필수 컬럼이 없거나 빈 데이터프레임일 경우
    """
    if df.empty:
        raise ValueError("빈 데이터프레임은 전처리할 수 없습니다.")
    
    required_columns = {'user_id', 'movie_id'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    
    if verbose:
        print("\n=== 전처리: ID 매핑 ===\n")
    
    # User ID 매핑 (문자열 -> 연속된 정수)
    unique_users = sorted(df['user_id'].unique())
    user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
    idx_to_user = {idx: user_id for user_id, idx in user_to_idx.items()}
    
    # Movie ID 매핑 (문자열 -> 연속된 정수)
    unique_movies = sorted(df['movie_id'].unique())
    movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
    idx_to_movie = {idx: movie_id for movie_id, idx in movie_to_idx.items()}
    
    # IDMapping 객체 생성
    id_mapping = IDMapping(
        user_to_idx=user_to_idx,
        idx_to_user=idx_to_user,
        movie_to_idx=movie_to_idx,
        idx_to_movie=idx_to_movie
    )
    
    # 새로운 컬럼 추가 (복사본에서)
    df_new = df.copy()
    df_new['user_idx'] = df_new['user_id'].map(user_to_idx)
    df_new['movie_idx'] = df_new['movie_id'].map(movie_to_idx)
    
    if verbose:
        print(f"사용자 매핑: {len(user_to_idx):,}명")
        print(f"  - 원본 예시: {list(user_to_idx.items())[:3]}")
        print(f"\n영화 매핑: {len(movie_to_idx):,}개")
        print(f"  - 원본 예시: {list(movie_to_idx.items())[:3]}")
        
        # 데이터 확인
        print("\n전처리된 데이터:")
        display_cols = ['user_id', 'user_idx', 'movie_id', 'movie_idx']
        if 'movie_title' in df_new.columns:
            display_cols.append('movie_title')
        if 'rating' in df_new.columns:
            display_cols.append('rating')
        print(df_new[display_cols].head(10).to_string(index=False))
        
        # 최종 데이터 통계
        print("\n=== 최종 데이터 통계 ===")
        print(f"사용자 수: {df_new['user_idx'].nunique():,}명")
        print(f"영화 수: {df_new['movie_idx'].nunique():,}개")
        print(f"평점 수: {len(df_new):,}개")
        if 'rating' in df_new.columns:
            print(f"평점 범위: {df_new['rating'].min():.1f} ~ {df_new['rating'].max():.1f}")
            print(f"평균 평점: {df_new['rating'].mean():.2f}")
    
    return df_new, id_mapping


def find_movie_id_by_title(
    movie_title: str,
    df: pd.DataFrame,
    exact_match: bool = False,
    limit: int = 10
) -> Optional[pd.DataFrame]:
    """
    영화 이름으로 영화 ID를 찾는 함수
    
    Args:
        movie_title: 검색할 영화 제목
        df: 영화 데이터가 포함된 데이터프레임 (movie_title, movie_id 컬럼 필수)
        exact_match: True이면 정확히 일치하는 영화만, False이면 부분 일치 허용
        limit: 반환할 최대 결과 개수 (부분 일치 검색 시)
        
    Returns:
        검색 결과 DataFrame (movie_id, movie_title 포함) 또는 None
        
    Raises:
        ValueError: 필수 컬럼이 없는 경우
    """
    required_columns = {'movie_title', 'movie_id'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    
    if exact_match:
        # 정확히 일치하는 영화 찾기
        result = df[df['movie_title'] == movie_title].copy()
    else:
        # 부분 일치 검색 (대소문자 구분 없이)
        result = df[df['movie_title'].str.contains(movie_title, case=False, na=False)].copy()
    
    if result.empty:
        print(f"'{movie_title}' 이름을 포함하는 영화를 찾을 수 없습니다.")
        return None
    
    # 중복 제거 (movie_id 기준)
    result = result.drop_duplicates(subset=['movie_id'])
    
    # limit 적용
    if len(result) > limit:
        result = result.head(limit)
        print(f"검색 결과가 {limit}개로 제한되었습니다. (총 {len(result)}개 이상)")
    
    # 필요한 컬럼만 선택
    display_cols = ['movie_id', 'movie_title']
    if 'movie_idx' in result.columns:
        display_cols.insert(0, 'movie_idx')
    
    return result[display_cols].reset_index(drop=True)


def get_movie_id(
    movie_title: str,
    df: pd.DataFrame
) -> Optional[str]:
    """
    영화 제목으로 단일 영화 ID를 반환하는 간단한 헬퍼 함수
    
    Args:
        movie_title: 검색할 영화 제목
        df: 영화 데이터가 포함된 데이터프레임
        
    Returns:
        영화 ID (문자열) 또는 None (찾지 못했거나 여러 개인 경우)
    """
    result = find_movie_id_by_title(movie_title, df, exact_match=True, limit=1)
    
    if result is None or len(result) == 0:
        # 정확히 일치하는 것이 없으면 부분 일치 시도
        result = find_movie_id_by_title(movie_title, df, exact_match=False, limit=5)
        if result is None or len(result) == 0:
            return None
        elif len(result) > 1:
            print("\n여러 영화가 검색되었습니다. 정확한 제목을 입력하세요:")
            print(result.to_string(index=False))
            return None
    
    return result.iloc[0]['movie_id']


def search_movies(df_movies: pd.DataFrame, query: str, limit: int = 10) -> pd.DataFrame:
    """영화 제목으로 검색"""
    result = df_movies[df_movies['title'].str.contains(query, case=False, na=False)]
    return result.head(limit)
