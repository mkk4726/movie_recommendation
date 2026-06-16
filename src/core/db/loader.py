"""
ML 원본 테이블을 DB에서 로드하고 parquet으로 캐시하는 모듈.

캐시가 있으면 DB 연결 없이 바로 반환하므로, DB가 끊겨 있어도 재사용 가능.
기본 캐시 경로: <project_root>/data/cache/
"""

import os
from pathlib import Path

import pandas as pd
import psycopg2

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_DEFAULT_CACHE_DIR = _PROJECT_ROOT / "data" / "cache"


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
        user=os.environ.get("POSTGRES_USER", "movie_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
    )


def load_ml_ratings(
    cache_dir: Path = _DEFAULT_CACHE_DIR,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    ml_ratings 테이블을 로드한다 (캐시 → DB 순서).

    컬럼: user_id (int), movie_id (int), rating (float), rated_at (datetime)

    Args:
        cache_dir: parquet 캐시를 저장할 디렉토리
        refresh: True이면 캐시를 무시하고 DB에서 다시 로드

    Returns:
        ml_ratings DataFrame
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "ml_ratings.parquet"

    if not refresh and cache_path.exists():
        print(f"캐시에서 로드: {cache_path}")
        return pd.read_parquet(cache_path)

    print("DB에서 ml_ratings 쿼리 중... (32M rows, 시간이 걸릴 수 있음)")
    conn = _connect()
    try:
        df = pd.read_sql_query(
            "SELECT user_id, movie_id, rating, rated_at FROM ml_ratings", conn
        )
    finally:
        conn.close()

    df["rated_at"] = pd.to_datetime(df["rated_at"], unit="s")
    df.to_parquet(cache_path, index=False)
    print(f"캐시 저장 완료: {cache_path} ({len(df):,} rows)")
    return df


def load_ml_movies(
    cache_dir: Path = _DEFAULT_CACHE_DIR,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    ml_movies 테이블을 로드한다 (캐시 → DB 순서).

    컬럼: movie_id (int), title (str), genres (str)

    Args:
        cache_dir: parquet 캐시를 저장할 디렉토리
        refresh: True이면 캐시를 무시하고 DB에서 다시 로드

    Returns:
        ml_movies DataFrame
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "ml_movies.parquet"

    if not refresh and cache_path.exists():
        print(f"캐시에서 로드: {cache_path}")
        return pd.read_parquet(cache_path)

    print("DB에서 ml_movies 쿼리 중...")
    conn = _connect()
    try:
        df = pd.read_sql_query(
            "SELECT movie_id, title, genres FROM ml_movies", conn
        )
    finally:
        conn.close()

    df.to_parquet(cache_path, index=False)
    print(f"캐시 저장 완료: {cache_path} ({len(df):,} rows)")
    return df
