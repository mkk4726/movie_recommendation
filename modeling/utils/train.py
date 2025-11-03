from typing import Tuple, Optional
import time
import pandas as pd
import numpy as np
import hashlib
from pathlib import Path


def split_train_test(
    df_ratings: Optional[pd.DataFrame] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    verbose: bool = True,
    refresh: bool = True,
    cache_dir: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    사용자와 영화가 train/test 세트 모두에 포함되도록 데이터를 분할하는 함수
    
    각 사용자의 평점을 일부는 train, 일부는 test로 분할하여
    모든 user_id와 movie_id가 양쪽 세트에 나타나도록 보장합니다.
    
    Args:
        df_ratings: 평점 데이터프레임 (user_id, movie_id, rating 컬럼 필수)
                   refresh=False이고 캐시가 있으면 None 가능 (기본값: None)
        test_size: 테스트 세트 비율 (0.0 ~ 1.0)
        random_state: 랜덤 시드
        verbose: 분할 정보 출력 여부
        refresh: True이면 캐시를 무시하고 새로 생성, False이면 캐시 사용 (기본값: True)
        cache_dir: 캐시 파일 저장 디렉토리 (기본값: modeling/utils/cache/)
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (df_train, df_test)
        
    Raises:
        ValueError: 필수 컬럼이 없거나 빈 데이터프레임일 경우, 또는 refresh=True인데 df_ratings가 None인 경우
    """
    # 캐시 디렉토리 설정
    if cache_dir is None:
        # 현재 파일 위치 기준으로 캐시 디렉토리 찾기
        # train.py -> modeling/utils/ -> modeling/utils/cache/
        current_file = Path(__file__).resolve()
        cache_dir = current_file.parent / 'cache'
    else:
        cache_dir = Path(cache_dir)
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 캐시에서 불러오기 (refresh=False이고 df_ratings가 None이거나 파일이 존재하는 경우)
    if not refresh:
        # df_ratings가 있으면 해시로 정확한 파일 찾기
        if df_ratings is not None:
            data_hash_input = f"{len(df_ratings)}_{df_ratings['user_id'].nunique()}_{df_ratings['movie_id'].nunique()}_{test_size}_{random_state}"
            data_hash = hashlib.md5(data_hash_input.encode()).hexdigest()[:12]
            cache_train_path = cache_dir / f"df_train_{data_hash}.csv"
            cache_test_path = cache_dir / f"df_test_{data_hash}.csv"
        else:
            # df_ratings가 없으면 캐시 디렉토리에서 가장 최근 파일 찾기
            train_files = sorted(cache_dir.glob("df_train_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
            test_files = sorted(cache_dir.glob("df_test_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not train_files or not test_files:
                raise ValueError("캐시 파일을 찾을 수 없습니다. df_ratings를 제공하거나 refresh=True로 설정하세요.")
            
            # 가장 최근 파일 사용
            cache_train_path = train_files[0]
            # 대응하는 test 파일 찾기 (같은 해시를 가진 파일)
            train_hash = cache_train_path.stem.replace("df_train_", "")
            cache_test_path = cache_dir / f"df_test_{train_hash}.csv"
            
            if not cache_test_path.exists():
                # 정확히 일치하는 파일이 없으면 가장 최근 test 파일 사용
                cache_test_path = test_files[0]
        
        if cache_train_path.exists() and cache_test_path.exists():
            if verbose:
                print("\n=== 캐시에서 Train/Test 데이터 로드 ===")
            start_time = time.time()
            df_train = pd.read_csv(str(cache_train_path))
            df_test = pd.read_csv(str(cache_test_path))
            if verbose:
                print(f"✅ 캐시 로드 완료: {time.time() - start_time:.2f}초")
                print(f"  - Train: {len(df_train):,}개")
                print(f"  - Test: {len(df_test):,}개")
                print(f"  - 파일: {cache_train_path.name}, {cache_test_path.name}")
            return df_train, df_test
        elif df_ratings is None:
            raise ValueError("캐시 파일을 찾을 수 없습니다. df_ratings를 제공하거나 refresh=True로 설정하세요.")
    
    # 새로 분할하려면 df_ratings가 필요
    if df_ratings is None:
        raise ValueError("새로 분할하려면 df_ratings가 필요합니다.")
    
    if df_ratings.empty:
        raise ValueError("빈 데이터프레임은 분할할 수 없습니다.")
    
    required_columns = {'user_id', 'movie_id', 'rating'}
    if not required_columns.issubset(df_ratings.columns):
        missing = required_columns - set(df_ratings.columns)
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")
    
    # 캐시 파일명 생성 (데이터 크기와 파라미터를 기반으로 해시 생성)
    data_hash_input = f"{len(df_ratings)}_{df_ratings['user_id'].nunique()}_{df_ratings['movie_id'].nunique()}_{test_size}_{random_state}"
    data_hash = hashlib.md5(data_hash_input.encode()).hexdigest()[:12]
    cache_train_path = cache_dir / f"df_train_{data_hash}.csv"
    cache_test_path = cache_dir / f"df_test_{data_hash}.csv"
    
    # 새로 분할
    start_time = time.time()
    
    if verbose:
        print("\n=== Train/Test Split ===")
        print(f"전체 평점 수: {len(df_ratings):,}개")
        print(f"사용자 수: {df_ratings['user_id'].nunique():,}명")
        print(f"영화 수: {df_ratings['movie_id'].nunique():,}개")
        print(f"Test size: {test_size:.1%}\n")
    
    # 벡터화된 방식으로 최적화 (32M 데이터 처리 최적화)
    step_start = time.time()
    np.random.seed(random_state)
    
    # 각 row에 랜덤 값 추가 (셔플링용)
    df_ratings_copy = df_ratings.copy()
    df_ratings_copy['_random'] = np.random.rand(len(df_ratings_copy))
    if verbose:
        print(f"[1/6] 데이터 복사 및 랜덤 값 생성: {time.time() - step_start:.2f}초")
    
    # user_id로 정렬 후 랜덤 값으로 재정렬 (각 user별로 랜덤하게 섞음)
    # sort_values는 매우 최적화되어 있음
    step_start = time.time()
    df_ratings_copy = df_ratings_copy.sort_values(['user_id', '_random']).reset_index(drop=True)
    if verbose:
        print(f"[2/6] 정렬 (user_id, _random): {time.time() - step_start:.2f}초")
    
    # 각 user별로 순차 인덱스 생성 (0부터 시작)
    # cumcount는 매우 빠른 벡터화된 연산
    step_start = time.time()
    df_ratings_copy['_pos'] = df_ratings_copy.groupby('user_id').cumcount()
    if verbose:
        print(f"[3/6] 그룹별 순차 인덱스 생성 (cumcount): {time.time() - step_start:.2f}초")
    
    # 각 user별 총 개수 계산 (map은 O(1) lookup)
    step_start = time.time()
    user_counts = df_ratings_copy.groupby('user_id').size()
    df_ratings_copy['_user_count'] = df_ratings_copy['user_id'].map(user_counts)
    if verbose:
        print(f"[4/6] 사용자별 평점 개수 계산: {time.time() - step_start:.2f}초")
    
    # 각 user별로 정규화된 위치 계산 (0~1 사이)
    # 평점이 1개만 있는 경우는 0으로 처리
    step_start = time.time()
    df_ratings_copy['_normalized_pos'] = np.where(
        df_ratings_copy['_user_count'] > 1,
        df_ratings_copy['_pos'] / (df_ratings_copy['_user_count'] - 1),
        0.0
    )
    
    # test_size 기준으로 test 여부 결정
    # 평점이 1개만 있는 user는 train에 포함 (user_count > 1 조건)
    df_ratings_copy['_is_test'] = (
        (df_ratings_copy['_user_count'] > 1) & 
        (df_ratings_copy['_normalized_pos'] < test_size)
    )
    if verbose:
        print(f"[5/6] 정규화 및 test 플래그 생성: {time.time() - step_start:.2f}초")
    
    # 한 번에 분할 (boolean indexing이 매우 빠름)
    step_start = time.time()
    df_train = df_ratings_copy[~df_ratings_copy['_is_test']].drop(
        columns=['_random', '_pos', '_user_count', '_normalized_pos', '_is_test']
    ).reset_index(drop=True)
    
    df_test = df_ratings_copy[df_ratings_copy['_is_test']].drop(
        columns=['_random', '_pos', '_user_count', '_normalized_pos', '_is_test']
    ).reset_index(drop=True)
    if verbose:
        print(f"[6/6] 데이터 분할: {time.time() - step_start:.2f}초")
        print(f"\n⏱️  전체 소요 시간: {time.time() - start_time:.2f}초\n")
    
    if verbose:
        print("✅ 분할 완료\n")
        
        step_start = time.time()
        print("Train set:")
        print(f"  - 평점 수: {len(df_train):,}개 ({len(df_train)/len(df_ratings):.1%})")
        print(f"  - 사용자 수: {df_train['user_id'].nunique():,}명")
        print(f"  - 영화 수: {df_train['movie_id'].nunique():,}개")
        print("\nTest set:")
        print(f"  - 평점 수: {len(df_test):,}개 ({len(df_test)/len(df_ratings):.1%})")
        print(f"  - 사용자 수: {df_test['user_id'].nunique():,}명")
        print(f"  - 영화 수: {df_test['movie_id'].nunique():,}개")
        print(f"  (통계 계산: {time.time() - step_start:.2f}초)")
        
        # 모든 user와 movie가 양쪽 세트에 포함되는지 확인
        step_start = time.time()
        train_users = set(df_train['user_id'].unique())
        test_users = set(df_test['user_id'].unique())
        train_movies = set(df_train['movie_id'].unique())
        test_movies = set(df_test['movie_id'].unique())
        
        all_users = set(df_ratings['user_id'].unique())
        all_movies = set(df_ratings['movie_id'].unique())
        
        users_in_both = train_users.intersection(test_users)
        movies_in_both = train_movies.intersection(test_movies)
        
        print("\n✅ 검증:")
        print(f"  - Train/Test 모두에 포함된 사용자: {len(users_in_both):,}명 / {len(all_users):,}명 ({len(users_in_both)/len(all_users)*100:.1f}%)")
        print(f"  - Train/Test 모두에 포함된 영화: {len(movies_in_both):,}개 / {len(all_movies):,}개 ({len(movies_in_both)/len(all_movies)*100:.1f}%)")
        
        # Train에만 있는 user/movie가 있는지 확인
        train_only_users = train_users - test_users
        train_only_movies = train_movies - test_movies
        
        if train_only_users:
            print(f"\n  ⚠️  Train에만 있는 사용자: {len(train_only_users)}명 (평점이 1개만 있는 사용자)")
        if train_only_movies:
            print(f"  ⚠️  Train에만 있는 영화: {len(train_only_movies)}개")
        
        print(f"\n  (검증 소요 시간: {time.time() - step_start:.2f}초)")
        print(f"\n⏱️  총 소요 시간: {time.time() - start_time:.2f}초\n")
    
    # 캐시에 저장
    if verbose:
        print("💾 캐시 파일 저장 중...")
    cache_start = time.time()
    df_train.to_csv(str(cache_train_path), index=False)
    df_test.to_csv(str(cache_test_path), index=False)
    if verbose:
        print(f"✅ 캐시 저장 완료: {time.time() - cache_start:.2f}초")
        print(f"  - {cache_train_path}")
        print(f"  - {cache_test_path}\n")
    
    return df_train, df_test


def optimize_dataframe_for_surprise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Surprise 라이브러리 사용을 위해 DataFrame을 최적화
    
    user_id와 movie_id를 category 타입으로 변환하여 메모리를 절약하고
    trainset 생성 속도를 향상시킵니다.
    
    Args:
        df: 최적화할 데이터프레임 (user_id, movie_id, rating 컬럼 필요)
        
    Returns:
        최적화된 DataFrame
    """
    df_optimized = df.copy()
    
    # category 타입으로 변환 (메모리 절약 + 속도 향상)
    if 'user_id' in df_optimized.columns:
        df_optimized['user_id'] = df_optimized['user_id'].astype('category')
    if 'movie_id' in df_optimized.columns:
        df_optimized['movie_id'] = df_optimized['movie_id'].astype('category')
    
    # rating은 float32로 변환 (메모리 절약)
    if 'rating' in df_optimized.columns:
        df_optimized['rating'] = df_optimized['rating'].astype('float32')
    
    return df_optimized