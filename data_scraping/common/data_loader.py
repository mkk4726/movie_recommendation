"""
영화 데이터 로딩 유틸리티
ML-32M, TMDB 데이터를 통합하여 로드합니다.
"""
import time
import pandas as pd
from data_scraping.common import (
    load_movie_data_ml,
    load_links_data_ml,
    load_ratings_data_ml,
    load_tmdb_data,
    get_logger,
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
    
    # total_title 생성: title_tmdb와 original_title이 같으면 title_tmdb만, 다르면 "title_tmdb (original_title)" 형식
    # NaN 처리: title_tmdb가 없으면 original_title 사용, 둘 다 없으면 빈 문자열
    title_tmdb = df['title_tmdb']
    original_title = df['original_title']
    
    # 두 제목이 모두 존재하고 같으면 title_tmdb만 사용
    mask_same = (title_tmdb == original_title) & title_tmdb.notna() & original_title.notna()
    
    # 두 제목이 모두 존재하고 다르면 "title_tmdb (original_title)" 형식
    mask_both_exist = title_tmdb.notna() & original_title.notna()
    mask_different = mask_both_exist & ~mask_same
    
    # total_title 초기화
    df['total_title'] = ''
    
    # 같은 경우: title_tmdb만 사용
    df.loc[mask_same, 'total_title'] = title_tmdb[mask_same]
    
    # 다른 경우: "title_tmdb (original_title)" 형식
    df.loc[mask_different, 'total_title'] = (
        title_tmdb[mask_different].astype(str) + ' (' + original_title[mask_different].astype(str) + ')'
    )
    
    # title_tmdb만 있는 경우
    mask_only_tmdb = title_tmdb.notna() & original_title.isna()
    df.loc[mask_only_tmdb, 'total_title'] = title_tmdb[mask_only_tmdb]
    
    # original_title만 있는 경우
    mask_only_original = title_tmdb.isna() & original_title.notna()
    df.loc[mask_only_original, 'total_title'] = original_title[mask_only_original]
    
    return df


def load_movie_cast() -> pd.DataFrame:
    """
    TMDB 영화 출연진 및 제작진 데이터 로드
    
    Returns:
        출연진/제작진 데이터 DataFrame
        컬럼: adult, gender, id, known_for_department, name, original_name, 
              popularity, profile_path, cast_id, character, credit_id, order, tmdb_id, imdb_id
    """
    import os
    from pathlib import Path
    
    # 프로젝트 루트에서 cast_data.csv 경로 찾기
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    cast_path = project_root / 'data_scraping' / 'data' / 'tmdb' / 'cast_data.csv'
    
    if not cast_path.exists():
        raise FileNotFoundError(f"Cast data file not found: {cast_path}")
    
    # Cast 데이터 로드
    df_cast = pd.read_csv(cast_path)
    
    # Links 데이터 로드하여 imdb_id 추가
    df_links = load_links_data_ml()
    
    # tmdb_id 타입 통일 (float으로)
    df_cast['tmdb_id'] = pd.to_numeric(df_cast['tmdb_id'], errors='coerce')
    df_links['tmdb_id'] = pd.to_numeric(df_links['tmdb_id'], errors='coerce')
    
    # tmdb_id를 기준으로 imdb_id 병합
    df_cast = pd.merge(
        df_cast,
        df_links[['tmdb_id', 'imdb_id']],
        on='tmdb_id',
        how='left'
    )
    
    return df_cast


def load_ratings_data(data_path: str = None, verbose: bool = False) -> pd.DataFrame:
    """
    ML-32M 사용자 평점 데이터 로딩
    
    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)
        verbose: 로그 출력 여부 (True면 상세 로그 출력)
    
    Returns:
        평점 정보 DataFrame
    """
    # Logger 설정
    logger = get_logger(__name__, level="INFO" if verbose else "CRITICAL")
    
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("평점 데이터 로딩 시작")
    logger.info("=" * 60)
    
    # 1. ML-32M 평점 데이터 로딩
    step_start = time.time()
    logger.info("[1/4] ML-32M 평점 데이터 로딩 중...")
    df_ratings = load_ratings_data_ml(data_path)
    step_time = time.time() - step_start
    logger.info(f"[1/4] 완료: {step_time:.2f}초 (행 수: {len(df_ratings):,})")
    
    # 2. 영화 데이터 로딩
    step_start = time.time()
    logger.info("[2/4] 영화 데이터 로딩 중...")
    df_movies = load_movie_data()
    step_time = time.time() - step_start
    logger.info(f"[2/4] 완료: {step_time:.2f}초 (영화 수: {len(df_movies):,})")
    
    # 3. 유효한 영화 ID 필터링
    step_start = time.time()
    logger.info("[3/4] 유효한 영화 ID 필터링 중...")
    # set을 사용하여 isin() 연산 성능 개선 (특히 큰 데이터셋에서 유용)
    valid_movie_ids = set(df_movies['movie_id'])
    df_ratings = df_ratings[df_ratings['movie_id'].isin(valid_movie_ids)].reset_index(drop=True)
    step_time = time.time() - step_start
    logger.info(f"[3/4] 완료: {step_time:.2f}초 (필터링 후 행 수: {len(df_ratings):,})")
    
    # 4. 타임스탬프 변환
    step_start = time.time()
    logger.info("[4/4] 타임스탬프 변환 중...")
    # apply 대신 pd.to_datetime 사용 (더 효율적)
    df_ratings['time'] = pd.to_datetime(df_ratings['timestamp'], unit='s')
    step_time = time.time() - step_start
    logger.info(f"[4/4] 완료: {step_time:.2f}초")
    
    # 총 소요 시간
    total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"전체 로딩 완료: {total_time:.2f}초")
    logger.info(f"최종 데이터 행 수: {len(df_ratings):,}")
    logger.info("=" * 60)
    
    return df_ratings