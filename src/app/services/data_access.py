"""
PostgreSQL 기반 영화 데이터 액세스 레이어.
CSV 파일 대신 PostgreSQL에서 영화/평점/출연진 데이터를 로드합니다.
"""

import os
from functools import lru_cache
from typing import Optional, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
        user=os.environ.get("POSTGRES_USER", "movie_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
    )


# TMDB 장르 ID → 한글 이름 매핑
_TMDB_GENRES = {
    28: "액션", 12: "모험", 16: "애니메이션", 35: "코미디", 80: "범죄",
    99: "다큐멘터리", 18: "드라마", 10751: "가족", 14: "판타지", 36: "역사",
    27: "공포", 10402: "음악", 9648: "미스터리", 10749: "로맨스", 878: "SF",
    10770: "TV 영화", 53: "스릴러", 10752: "전쟁", 37: "서부",
}


def _genre_ids_to_text(genre_ids) -> Optional[str]:
    if not genre_ids:
        return None
    names = [_TMDB_GENRES.get(gid, "") for gid in genre_ids if gid in _TMDB_GENRES]
    return " ".join(names) if names else None


def _build_total_title(title_tmdb, original_title) -> str:
    t = title_tmdb or ""
    o = original_title or ""
    if not t and not o:
        return ""
    if not t:
        return o
    if not o or t == o:
        return t
    return f"{t} ({o})"


@lru_cache(maxsize=1)
def load_movie_data() -> pd.DataFrame:
    """
    ml_movies + ml_links + tmdb_movies를 JOIN하여 통합 영화 DataFrame 반환.

    컬럼: movie_id(str), title, genres, imdb_id, tmdb_id,
          title_tmdb, original_title, total_title,
          overview, poster_path, backdrop_path, release_date,
          original_language, genre_ids, genres_tmdb, language,
          popularity, vote_average, vote_count, adult, media_type
    """
    sql = """
        SELECT
            m.movie_id,
            m.title,
            m.genres,
            l.imdb_id,
            l.tmdb_id,
            t.title          AS title_tmdb,
            t.original_title,
            t.overview,
            t.poster_path,
            t.backdrop_path,
            t.release_date,
            t.original_language,
            t.genre_ids,
            t.popularity,
            t.vote_average,
            t.vote_count,
            t.adult,
            t.media_type
        FROM ml_movies   m
        JOIN ml_links    l ON m.movie_id = l.movie_id
        JOIN tmdb_movies t ON l.tmdb_id  = t.tmdb_id
    """
    conn = _connect()
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()

    df["movie_id"] = df["movie_id"].astype(str)
    df["total_title"] = df.apply(
        lambda r: _build_total_title(r["title_tmdb"], r["original_title"]), axis=1
    )
    df["genres_tmdb"] = df["genre_ids"].apply(_genre_ids_to_text)
    df["language"] = df["original_language"]

    # year: release_date에서 연도 파싱
    df["year"] = pd.to_numeric(
        df["release_date"].str[:4], errors="coerce"
    ).astype("Int64")

    return df.reset_index(drop=True)


def load_all_data(
    min_user_ratings: Optional[int] = None,
    min_movie_ratings: Optional[int] = None,
) -> Tuple[pd.DataFrame, None, None]:
    """영화 데이터를 반환합니다. ratings는 더 이상 메모리에 올리지 않습니다."""
    return load_movie_data(), None, None


def user_exists(user_id: str) -> bool:
    """해당 user_id가 ml_ratings에 존재하는지 DB에서 확인합니다."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM ml_ratings WHERE user_id = %s LIMIT 1", (user_id,))
            return cur.fetchone() is not None
    finally:
        conn.close()


@lru_cache(maxsize=4)
def get_popular_movie_ids(top_n: int = 200) -> list:
    """평점이 많은 상위 top_n 영화의 movie_id 리스트를 반환합니다. (캐시됨)"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT movie_id FROM ml_ratings GROUP BY movie_id ORDER BY COUNT(*) DESC LIMIT %s",
                (top_n,),
            )
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        conn.close()


@lru_cache(maxsize=1)
def get_sample_user_ids(limit: int = 100) -> list:
    """ml_ratings에서 user_id 샘플을 반환합니다. (캐시됨)"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT user_id FROM ml_ratings ORDER BY user_id LIMIT %s", (limit,))
            return [str(row[0]) for row in cur.fetchall()]
    finally:
        conn.close()


@lru_cache(maxsize=1)
def load_cast_data() -> pd.DataFrame:
    """
    tmdb_cast + ml_links를 JOIN하여 출연진 DataFrame 반환.
    실제 사용 컬럼만 로드: imdb_id, cast_id, name, original_name,
    character, known_for_department, profile_path
    """
    sql = """
        SELECT
            l.imdb_id,
            c.cast_id,
            c.name,
            c.original_name,
            c.character,
            c.known_for_dept    AS known_for_department,
            c.profile_path
        FROM tmdb_cast c
        LEFT JOIN ml_links l ON c.tmdb_id = l.tmdb_id
    """
    conn = _connect()
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()

    df["cast_id"] = df["cast_id"].astype("int32")
    df["known_for_department"] = df["known_for_department"].astype("category")

    return df.reset_index(drop=True)


def invalidate_data_cache() -> None:
    """캐시 초기화 (데이터 갱신 후 호출)"""
    load_movie_data.cache_clear()
    load_cast_data.cache_clear()
    search_movies_cached.cache_clear()
    get_popular_movie_ids.cache_clear()
    get_sample_user_ids.cache_clear()


@lru_cache(maxsize=64)
def search_movies_cached(query: str, limit: int = 10) -> pd.DataFrame:
    """제목으로 영화 검색 (캐시 적용)."""
    normalized = (query or "").strip().lower()
    if not normalized:
        return pd.DataFrame()

    df_movies = load_movie_data()
    mask = (
        df_movies["title"].str.lower().str.contains(normalized, na=False) |
        df_movies["total_title"].str.lower().str.contains(normalized, na=False)
    )
    return df_movies[mask].head(limit).copy()


@lru_cache(maxsize=1)
def get_data_stats() -> dict:
    """PostgreSQL에서 데이터 통계를 쿼리합니다."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tmdb_movies")
            total_movies = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ml_ratings")
            total_ratings = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM ml_ratings")
            total_users = cur.fetchone()[0]
            cur.execute("SELECT AVG(rating) FROM ml_ratings")
            avg_rating = cur.fetchone()[0]
    finally:
        conn.close()

    return {
        "total_movies": f"{total_movies:,}",
        "total_ratings": f"{total_ratings:,}",
        "total_users": f"{total_users:,}",
        "avg_rating": float(avg_rating) if avg_rating else None,
    }
