import hashlib
import os
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import psycopg2
import yaml
from surprise import Dataset, Reader
from surprise.trainset import Trainset

from core.modeling.utils.train import optimize_dataframe_for_surprise, split_train_test


def _connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
        user=os.environ.get("POSTGRES_USER", "movie_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
    )


def _load_data_config() -> dict:
    config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "data.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_ratings_from_pg() -> pd.DataFrame:
    """PostgreSQL ml_ratings에서 평점 로드."""
    sql = "SELECT user_id::text, movie_id::text, rating FROM ml_ratings"
    conn = _connect()
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


def load_train_test_df(
    data_config: dict, test_size: float = 0.2, refresh: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Train/Test 데이터를 로드 (캐시 → PostgreSQL 순서).

    Args:
        data_config: {"data": {"min_user_ratings": int, "min_movie_ratings": int}}
        test_size: 테스트 세트 비율
        refresh: True이면 캐시 무시

    Returns:
        (df_train, df_test)
    """
    cache_dir = Path(__file__).parent
    cache_dir.mkdir(parents=True, exist_ok=True)

    min_user_ratings = data_config["data"]["min_user_ratings"]
    min_movie_ratings = data_config["data"]["min_movie_ratings"]
    cache_key = f"{min_user_ratings}_{min_movie_ratings}_{test_size}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]

    cache_train_path = cache_dir / f"cache_train_{cache_hash}.csv"
    cache_test_path = cache_dir / f"cache_test_{cache_hash}.csv"

    if not refresh and cache_train_path.exists() and cache_test_path.exists():
        print(f"\n✅ 캐시에서 Train/Test 데이터 로드: {cache_train_path.name}")
        df_train = pd.read_csv(cache_train_path, dtype={"user_id": str, "movie_id": str})
        df_test = pd.read_csv(cache_test_path, dtype={"user_id": str, "movie_id": str})
        return df_train, df_test

    print("\n📥 PostgreSQL에서 평점 데이터 로드 중...")
    from core.modeling.utils.data import filter_by_min_counts
    df_ratings = _load_ratings_from_pg()

    print("\n🔍 데이터 필터링 중...")
    df_filtered = filter_by_min_counts(
        df_ratings,
        min_user_ratings=min_user_ratings,
        min_movie_ratings=min_movie_ratings,
    )

    print("\n✂️  Train/Test 분할 중...")
    df_train, df_test = split_train_test(df_filtered, test_size=test_size, verbose=True)

    print("\n💾 캐시 파일 저장 중...")
    df_train.to_csv(cache_train_path, index=False)
    df_test.to_csv(cache_test_path, index=False)
    print(f"✅ 캐시 저장 완료: {cache_train_path.name}, {cache_test_path.name}\n")

    return df_train, df_test


def load_trainset_testset() -> Tuple[Trainset, List[Tuple[str, str, float]]]:
    """Train/Test 데이터를 Surprise 형식으로 로드."""
    data_config_dict = _load_data_config()
    df_train, df_test = load_train_test_df(data_config_dict, refresh=False)

    df_train_opt = optimize_dataframe_for_surprise(df_train[["user_id", "movie_id", "rating"]])
    df_test_opt = optimize_dataframe_for_surprise(df_test[["user_id", "movie_id", "rating"]])

    reader = Reader(rating_scale=(0.5, 5.0))
    train_data = Dataset.load_from_df(df_train_opt, reader)
    trainset = train_data.build_full_trainset()
    testset = [tuple(x) for x in df_test_opt[["user_id", "movie_id", "rating"]].values]

    return trainset, testset


def load_totalset() -> Trainset:
    """전체 데이터를 Surprise 형식의 trainset으로 로드."""
    data_config_dict = _load_data_config()
    df_train, df_test = load_train_test_df(data_config_dict, refresh=False)
    df_total = pd.concat([df_train, df_test], ignore_index=True)

    df_total_opt = optimize_dataframe_for_surprise(df_total[["user_id", "movie_id", "rating"]])

    reader = Reader(rating_scale=(0.5, 5.0))
    total_data = Dataset.load_from_df(df_total_opt, reader)
    return total_data.build_full_trainset()
