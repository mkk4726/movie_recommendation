import logging
import sys
import time
from typing import Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
# 기본 handler가 없으면 추가
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def split_train_test(
    df_ratings: pd.DataFrame, test_size: float = 0.2, random_state: int = 42, verbose: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    사용자와 영화가 train/test 세트 모두에 포함되도록 데이터를 분할하는 함수

    각 사용자의 평점을 일부는 train, 일부는 test로 분할하여
    모든 user_id와 movie_id가 양쪽 세트에 나타나도록 보장합니다.

    Args:
        df_ratings: 평점 데이터프레임 (user_id, movie_id, rating 컬럼 필수)
        test_size: 테스트 세트 비율 (0.0 ~ 1.0)
        random_state: 랜덤 시드
        verbose: 분할 정보 출력 여부

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (df_train, df_test)

    Raises:
        ValueError: 필수 컬럼이 없거나 빈 데이터프레임일 경우
    """
    # logger level 설정
    logger.setLevel(logging.INFO if verbose else logging.WARNING)

    if df_ratings.empty:
        raise ValueError("빈 데이터프레임은 분할할 수 없습니다.")

    required_columns = {"user_id", "movie_id", "rating"}
    if not required_columns.issubset(df_ratings.columns):
        missing = required_columns - set(df_ratings.columns)
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")

    # 데이터 분할
    start_time = time.time()

    logger.info("\n=== Train/Test Split ===")
    logger.info(f"전체 평점 수: {len(df_ratings):,}개")
    logger.info(f"사용자 수: {df_ratings['user_id'].nunique():,}명")
    logger.info(f"영화 수: {df_ratings['movie_id'].nunique():,}개")
    logger.info(f"Test size: {test_size:.1%}\n")

    # 벡터화된 방식으로 최적화 (32M 데이터 처리 최적화)
    step_start = time.time()
    np.random.seed(random_state)

    # 각 row에 랜덤 값 추가 (셔플링용)
    df_ratings_copy = df_ratings.copy()
    df_ratings_copy["_random"] = np.random.rand(len(df_ratings_copy))
    logger.info(f"[1/6] 데이터 복사 및 랜덤 값 생성: {time.time() - step_start:.2f}초")

    # user_id로 정렬 후 랜덤 값으로 재정렬 (각 user별로 랜덤하게 섞음)
    # sort_values는 매우 최적화되어 있음
    step_start = time.time()
    df_ratings_copy = df_ratings_copy.sort_values(["user_id", "_random"]).reset_index(drop=True)
    logger.info(f"[2/6] 정렬 (user_id, _random): {time.time() - step_start:.2f}초")

    # 각 user별로 순차 인덱스 생성 (0부터 시작)
    # cumcount는 매우 빠른 벡터화된 연산
    step_start = time.time()
    df_ratings_copy["_pos"] = df_ratings_copy.groupby("user_id").cumcount()
    logger.info(f"[3/6] 그룹별 순차 인덱스 생성 (cumcount): {time.time() - step_start:.2f}초")

    # 각 user별 총 개수 계산 (map은 O(1) lookup)
    step_start = time.time()
    user_counts = df_ratings_copy.groupby("user_id").size()
    df_ratings_copy["_user_count"] = df_ratings_copy["user_id"].map(user_counts)
    logger.info(f"[4/6] 사용자별 평점 개수 계산: {time.time() - step_start:.2f}초")

    # 각 user별로 정규화된 위치 계산 (0~1 사이)
    # 평점이 1개만 있는 경우는 0으로 처리
    step_start = time.time()
    df_ratings_copy["_normalized_pos"] = np.where(
        df_ratings_copy["_user_count"] > 1, df_ratings_copy["_pos"] / (df_ratings_copy["_user_count"] - 1), 0.0
    )

    # test_size 기준으로 test 여부 결정
    # 평점이 1개만 있는 user는 train에 포함 (user_count > 1 조건)
    df_ratings_copy["_is_test"] = (df_ratings_copy["_user_count"] > 1) & (
        df_ratings_copy["_normalized_pos"] < test_size
    )
    logger.info(f"[5/6] 정규화 및 test 플래그 생성: {time.time() - step_start:.2f}초")

    # 한 번에 분할 (boolean indexing이 매우 빠름)
    step_start = time.time()
    df_train = (
        df_ratings_copy[~df_ratings_copy["_is_test"]]
        .drop(columns=["_random", "_pos", "_user_count", "_normalized_pos", "_is_test"])
        .reset_index(drop=True)
    )

    df_test = (
        df_ratings_copy[df_ratings_copy["_is_test"]]
        .drop(columns=["_random", "_pos", "_user_count", "_normalized_pos", "_is_test"])
        .reset_index(drop=True)
    )
    logger.info(f"[6/6] 데이터 분할: {time.time() - step_start:.2f}초")
    logger.info(f"\n⏱️  전체 소요 시간: {time.time() - start_time:.2f}초\n")

    logger.info("✅ 분할 완료\n")

    step_start = time.time()
    logger.info("Train set:")
    logger.info(f"  - 평점 수: {len(df_train):,}개 ({len(df_train) / len(df_ratings):.1%})")
    logger.info(f"  - 사용자 수: {df_train['user_id'].nunique():,}명")
    logger.info(f"  - 영화 수: {df_train['movie_id'].nunique():,}개")
    logger.info("\nTest set:")
    logger.info(f"  - 평점 수: {len(df_test):,}개 ({len(df_test) / len(df_ratings):.1%})")
    logger.info(f"  - 사용자 수: {df_test['user_id'].nunique():,}명")
    logger.info(f"  - 영화 수: {df_test['movie_id'].nunique():,}개")
    logger.info(f"  (통계 계산: {time.time() - step_start:.2f}초)")

    # 모든 user와 movie가 양쪽 세트에 포함되는지 확인
    step_start = time.time()
    train_users = set(df_train["user_id"].unique())
    test_users = set(df_test["user_id"].unique())
    train_movies = set(df_train["movie_id"].unique())
    test_movies = set(df_test["movie_id"].unique())

    all_users = set(df_ratings["user_id"].unique())
    all_movies = set(df_ratings["movie_id"].unique())

    users_in_both = train_users.intersection(test_users)
    movies_in_both = train_movies.intersection(test_movies)

    logger.info("\n✅ 검증:")
    logger.info(
        f"  - Train/Test 모두에 포함된 사용자: {len(users_in_both):,}명 / {len(all_users):,}명 ({len(users_in_both) / len(all_users) * 100:.1f}%)"
    )
    logger.info(
        f"  - Train/Test 모두에 포함된 영화: {len(movies_in_both):,}개 / {len(all_movies):,}개 ({len(movies_in_both) / len(all_movies) * 100:.1f}%)"
    )

    # Train에만 있는 user/movie가 있는지 확인
    train_only_users = train_users - test_users
    train_only_movies = train_movies - test_movies

    if train_only_users:
        logger.info(f"\n  ⚠️  Train에만 있는 사용자: {len(train_only_users)}명 (평점이 1개만 있는 사용자)")
    if train_only_movies:
        logger.info(f"  ⚠️  Train에만 있는 영화: {len(train_only_movies)}개")

    logger.info(f"\n  (검증 소요 시간: {time.time() - step_start:.2f}초)")
    logger.info(f"\n⏱️  총 소요 시간: {time.time() - start_time:.2f}초\n")

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
    if "user_id" in df_optimized.columns:
        df_optimized["user_id"] = df_optimized["user_id"].astype("category")
    if "movie_id" in df_optimized.columns:
        df_optimized["movie_id"] = df_optimized["movie_id"].astype("category")

    # rating은 float32로 변환 (메모리 절약)
    if "rating" in df_optimized.columns:
        df_optimized["rating"] = df_optimized["rating"].astype("float32")

    return df_optimized
