import hashlib
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import yaml
from surprise import Dataset, Reader
from surprise.trainset import Trainset

from data_scraping.common.data_loader import load_ratings_data
from modeling.utils.data import filter_by_min_counts
from modeling.utils.train import optimize_dataframe_for_surprise, split_train_test


def load_train_test_df(
    data_config: dict, test_size: float = 0.2, refresh: bool = False
) -> [pd.DataFrame, pd.DataFrame]:
    """
    Train/Test 데이터를 로드하는 함수 (캐시 지원)

    Args:
        data_config: 데이터 설정 딕셔너리 (data.min_user_ratings, data.min_movie_ratings 포함)
        test_size: 테스트 세트 비율 (기본값: 0.2)
        refresh: True이면 캐시를 무시하고 새로 생성 (기본값: False)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (df_train, df_test)
    """
    # 캐시 디렉토리 설정 (dataloader.py와 같은 위치)
    cache_dir = Path(__file__).parent
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 캐시 키 생성 (data_config와 test_size 기반)
    min_user_ratings = data_config["data"]["min_user_ratings"]
    min_movie_ratings = data_config["data"]["min_movie_ratings"]
    cache_key = f"{min_user_ratings}_{min_movie_ratings}_{test_size}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]

    cache_train_path = cache_dir / f"cache_train_{cache_hash}.csv"
    cache_test_path = cache_dir / f"cache_test_{cache_hash}.csv"

    # 캐시에서 로드 시도 (refresh=False이고 파일이 존재하는 경우)
    if not refresh and cache_train_path.exists() and cache_test_path.exists():
        print(f"\n✅ 캐시에서 Train/Test 데이터 로드: {cache_train_path.name}")
        df_train = pd.read_csv(cache_train_path, dtype={"user_id": str, "movie_id": str})
        df_test = pd.read_csv(cache_test_path, dtype={"user_id": str, "movie_id": str})
        return df_train, df_test

    # 새로 생성
    print("\n📥 데이터 로드 및 처리 중...")
    df_ratings = load_ratings_data(verbose=True)

    print("\n🔍 데이터 필터링 중...")
    df_filtered = filter_by_min_counts(
        df_ratings, min_user_ratings=min_user_ratings, min_movie_ratings=min_movie_ratings
    )

    print("\n✂️  Train/Test 분할 중...")
    df_train, df_test = split_train_test(df_filtered, test_size=test_size, verbose=True)

    # 캐시에 저장
    print("\n💾 캐시 파일 저장 중...")
    df_train.to_csv(cache_train_path, index=False)
    df_test.to_csv(cache_test_path, index=False)
    print(f"✅ 캐시 저장 완료: {cache_train_path.name}, {cache_test_path.name}\n")

    return df_train, df_test


def load_trainset_testset() -> Tuple[Trainset, List[Tuple[str, str, float]]]:
    """
    Train/Test 데이터를 Surprise 라이브러리 형식으로 로드하는 함수

    Returns:
        Tuple[Trainset, List[Tuple[str, str, float]]]: (trainset, testset)
    """
    data_config_path = Path(__file__).parent.parent.parent / "utils" / "data_config.yaml"
    with open(data_config_path, "r", encoding="utf-8") as f:
        data_config_dict = yaml.safe_load(f)

    df_train, df_test = load_train_test_df(data_config_dict, refresh=False)

    # DataFrame 최적화 (trainset 생성 속도 향상)
    df_train_opt = optimize_dataframe_for_surprise(df_train[["user_id", "movie_id", "rating"]])
    df_test_opt = optimize_dataframe_for_surprise(df_test[["user_id", "movie_id", "rating"]])

    # Reader 객체 생성 (평점 범위 지정)
    reader = Reader(rating_scale=(0.5, 5.0))

    train_data = Dataset.load_from_df(df_train_opt, reader)
    trainset = train_data.build_full_trainset()
    testset = [tuple(x) for x in df_test_opt[["user_id", "movie_id", "rating"]].values]

    return trainset, testset


def load_totalset() -> Trainset:
    """
    전체 데이터를 Surprise 라이브러리 형식의 trainset으로 로드하는 함수
    (Train과 Test를 합친 전체 데이터셋)

    Returns:
        Trainset: 전체 데이터로 구성된 trainset
    """
    data_config_path = Path(__file__).parent.parent.parent / "utils" / "data_config.yaml"
    with open(data_config_path, "r", encoding="utf-8") as f:
        data_config_dict = yaml.safe_load(f)

    df_train, df_test = load_train_test_df(data_config_dict, refresh=False)
    df_total = pd.concat([df_train, df_test], ignore_index=True)

    # DataFrame 최적화 (trainset 생성 속도 향상)
    df_total_opt = optimize_dataframe_for_surprise(df_total[["user_id", "movie_id", "rating"]])

    # Reader 객체 생성 (평점 범위 지정)
    reader = Reader(rating_scale=(0.5, 5.0))

    total_data = Dataset.load_from_df(df_total_opt, reader)
    totalset = total_data.build_full_trainset()

    return totalset
