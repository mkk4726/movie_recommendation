"""
데이터 로더 테스트

실제 데이터 파일이 필요한 테스트는 @pytest.mark.slow로 마킹합니다.
데이터가 없으면 자동으로 skip됩니다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────

def _data_available() -> bool:
    """PostgreSQL에서 영화 데이터가 조회 가능한지 확인"""
    try:
        import os
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
            user=os.environ.get("POSTGRES_USER", "movie_user"),
            password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ml_movies")
            count = cur.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


needs_data = pytest.mark.skipif(not _data_available(), reason="DB에 영화 데이터 없음")


# ─── data_access 레이어 ──────────────────────────────────────────────────────

class TestDataAccess:
    @needs_data
    @pytest.mark.slow
    def test_load_all_data_returns_dataframes(self):
        from app.modules.services.data_access import load_all_data
        df_movies, df_ratings, df_filtered = load_all_data()

        assert df_movies is not None and len(df_movies) > 0
        assert df_ratings is not None and len(df_ratings) > 0
        assert df_filtered is not None

    @needs_data
    @pytest.mark.slow
    def test_df_movies_has_required_columns(self):
        from app.modules.services.data_access import load_all_data
        df_movies, _, _ = load_all_data()

        required = {"movie_id", "title"}
        assert required.issubset(set(df_movies.columns))

    @needs_data
    @pytest.mark.slow
    def test_search_movies_cached_returns_results(self):
        from app.modules.services.data_access import search_movies_cached
        results = search_movies_cached("The Matrix", limit=5)

        assert results is not None
        assert len(results) > 0

    @needs_data
    @pytest.mark.slow
    def test_search_movies_limit_respected(self):
        from app.modules.services.data_access import search_movies_cached
        results = search_movies_cached("star", limit=3)
        assert len(results) <= 3

    @needs_data
    @pytest.mark.slow
    def test_get_data_stats_returns_valid_counts(self):
        from app.modules.services.data_access import get_data_stats
        stats = get_data_stats()

        assert stats["total_movies"] > 0
        assert stats["total_users"] > 0
        assert stats["total_ratings"] > 0
        assert 0.0 <= stats["avg_rating"] <= 5.0


# ─── core data_scraping 레이어 ───────────────────────────────────────────────

class TestCoreDataLoader:
    @needs_data
    @pytest.mark.slow
    def test_load_movie_data_returns_dataframe(self):
        from core.data_scraping.common.data_loader import load_movie_data
        df = load_movie_data()

        assert df is not None
        assert len(df) > 0
        assert "movie_id" in df.columns

    @needs_data
    @pytest.mark.slow
    def test_load_ratings_data_returns_dataframe(self):
        from core.data_scraping.common.data_loader import load_ratings_data
        df = load_ratings_data()

        assert df is not None
        assert len(df) > 0
        required = {"user_id", "movie_id", "rating"}
        assert required.issubset(set(df.columns))

    @needs_data
    @pytest.mark.slow
    def test_ratings_in_valid_range(self):
        from core.data_scraping.common.data_loader import load_ratings_data
        df = load_ratings_data()

        assert df["rating"].min() >= 0.5
        assert df["rating"].max() <= 5.0
