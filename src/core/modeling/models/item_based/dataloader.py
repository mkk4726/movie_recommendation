"""
Item-Based Collaborative Filtering 데이터 로더
PostgreSQL 기반, 캐시 기능 포함
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg2
import yaml

from core.modeling.utils.data import filter_by_min_counts


def _connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
        user=os.environ.get("POSTGRES_USER", "movie_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
    )


def load_data(refresh: bool = False, data_config_path: Optional[str] = None) -> pd.DataFrame:
    """
    Item-Based CF용 필터링된 데이터 로드 (캐시 → PostgreSQL 순서).

    Args:
        refresh: True이면 캐시 무시
        data_config_path: data.yaml 경로 (None이면 src/config/data.yaml)

    Returns:
        필터링된 평점 DataFrame
    """
    if data_config_path is None:
        data_config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "data.yaml"
    else:
        data_config_path = Path(data_config_path)

    print(f"📄 데이터 설정 파일 로드: {data_config_path}")
    with open(data_config_path, "r", encoding="utf-8") as f:
        data_config_dict = yaml.safe_load(f)

    data_config = data_config_dict["data"]
    min_user_ratings = data_config.get("min_user_ratings", 10)
    min_movie_ratings = data_config.get("min_movie_ratings", 30)

    cache_dir = Path(__file__).parent
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = f"{min_user_ratings}_{min_movie_ratings}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
    cache_path = cache_dir / f"cache_item_based_{cache_hash}.csv"

    if not refresh and cache_path.exists():
        print(f"\n✅ 캐시에서 데이터 로드: {cache_path.name}")
        filtered_data = pd.read_csv(cache_path, dtype={"user_id": str, "movie_id": str})
        print(f"  - 캐시된 데이터: {len(filtered_data):,}개 평점\n")
        return filtered_data

    print("\n📥 PostgreSQL에서 평점 데이터 로드 중...")
    conn = _connect()
    try:
        df_ratings = pd.read_sql_query(
            "SELECT user_id::text, movie_id::text, rating FROM ml_ratings", conn
        )
    finally:
        conn.close()
    print(f"  - 데이터: {len(df_ratings):,}개 평점")

    print(f"🔍 필터링: 사용자 최소 {min_user_ratings}개, 영화 최소 {min_movie_ratings}개")
    filtered_data = filter_by_min_counts(
        df_ratings,
        min_movie_ratings=min_movie_ratings,
        min_user_ratings=min_user_ratings,
    )
    print(f"  - 필터링 후: {len(filtered_data):,}개 평점")

    print("\n💾 캐시 저장 중...")
    filtered_data.to_csv(cache_path, index=False)
    print(f"✅ 캐시 저장 완료: {cache_path.name}\n")

    return filtered_data
