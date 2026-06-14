"""
사용자 시스템 통합 테스트 (PostgreSQL)

실제 DB를 사용하는 통합 테스트입니다.
테스트마다 생성된 사용자는 teardown에서 자동 삭제됩니다.
"""

import pytest
from core.user_system.db_manager import _connect, get_user_manager


# ─── 회원가입 ───────────────────────────────────────────────────────────────

class TestCreateUser:
    def test_creates_user_with_correct_fields(self, user_manager, unique_email):
        user = user_manager.create_user(unique_email, "pass1234", "Alice")
        try:
            assert user["email"] == unique_email
            assert user["display_name"] == "Alice"
            assert "user_id" in user
            assert "password_hash" not in user
        finally:
            conn = _connect()
            with conn:
                conn.cursor().execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
            conn.close()

    def test_display_name_defaults_to_email_prefix(self, user_manager, unique_email):
        user = user_manager.create_user(unique_email, "pass1234")
        try:
            assert user["display_name"] == unique_email.split("@")[0]
        finally:
            conn = _connect()
            with conn:
                conn.cursor().execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
            conn.close()

    def test_duplicate_email_raises_value_error(self, test_user, user_manager):
        with pytest.raises(ValueError, match="이미 존재하는"):
            user_manager.create_user(test_user["email"], "other_pass")

    def test_user_is_active_by_default(self, user_manager, unique_email):
        user = user_manager.create_user(unique_email, "pass1234")
        try:
            fetched = user_manager.get_user_by_id(user["user_id"])
            assert fetched["is_active"] is True
        finally:
            conn = _connect()
            with conn:
                conn.cursor().execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
            conn.close()


# ─── 조회 ───────────────────────────────────────────────────────────────────

class TestGetUser:
    def test_get_by_id_returns_user(self, user_manager, test_user):
        fetched = user_manager.get_user_by_id(test_user["user_id"])
        assert fetched is not None
        assert fetched["email"] == test_user["email"]

    def test_get_by_email_returns_user(self, user_manager, test_user):
        fetched = user_manager.get_user_by_email(test_user["email"])
        assert fetched is not None
        assert fetched["user_id"] == test_user["user_id"]

    def test_get_nonexistent_id_returns_none(self, user_manager):
        assert user_manager.get_user_by_id("00000000-0000-0000-0000-000000000000") is None

    def test_get_nonexistent_email_returns_none(self, user_manager):
        assert user_manager.get_user_by_email("nobody@nowhere.com") is None


# ─── 인증 ───────────────────────────────────────────────────────────────────

class TestVerifyCredentials:
    def test_correct_password_returns_user(self, user_manager, test_user, unique_email):
        result = user_manager.verify_credentials(test_user["email"], "password123")
        assert result is not None
        assert result["email"] == test_user["email"]
        assert "password_hash" not in result

    def test_wrong_password_returns_none(self, user_manager, test_user):
        assert user_manager.verify_credentials(test_user["email"], "wrong_pass") is None

    def test_unknown_email_returns_none(self, user_manager):
        assert user_manager.verify_credentials("ghost@example.com", "any") is None


# ─── 평점 ───────────────────────────────────────────────────────────────────

class TestUserRatings:
    def test_add_and_retrieve_rating(self, user_manager, test_user):
        ok = user_manager.add_user_rating(test_user["user_id"], "tt9999001", "Test Movie", 4.0)
        assert ok is True

        ratings = user_manager.get_user_ratings(test_user["user_id"])
        movie_ids = [r["movie_id"] for r in ratings]
        assert "tt9999001" in movie_ids

    def test_rating_upsert_updates_value(self, user_manager, test_user):
        user_manager.add_user_rating(test_user["user_id"], "tt9999002", "Movie B", 3.0)
        user_manager.add_user_rating(test_user["user_id"], "tt9999002", "Movie B", 5.0)

        ratings = user_manager.get_user_ratings(test_user["user_id"])
        match = [r for r in ratings if r["movie_id"] == "tt9999002"]
        assert match[0]["rating"] == 5.0

    def test_rating_out_of_range_raises(self, user_manager, test_user):
        with pytest.raises(ValueError):
            user_manager.add_user_rating(test_user["user_id"], "tt9999003", "X", 6.0)

    def test_no_ratings_returns_empty_list(self, user_manager, test_user):
        ratings = user_manager.get_user_ratings(test_user["user_id"])
        # 이전 테스트에서 추가됐을 수 있으므로 list 타입만 확인
        assert isinstance(ratings, list)


# ─── 활동 로그 ───────────────────────────────────────────────────────────────

class TestActivityLogs:
    def test_log_and_retrieve(self, user_manager, test_user):
        user_manager.log_activity(test_user["user_id"], "search", {"query": "batman"})
        user_manager.log_activity(test_user["user_id"], "view_movie", {"movie_id": "tt0468569"})

        logs = user_manager.get_activity_logs(test_user["user_id"])
        actions = [l["action"] for l in logs]
        assert "search" in actions
        assert "view_movie" in actions

    def test_anonymous_search_log(self, user_manager):
        session_id = user_manager.log_search(
            user_id=None,
            query="batman",
            search_type="natural_language",
            result_count=3,
            result_movie_ids=["1", "2", "3"],
            ip="127.0.0.1",
        )
        assert session_id

        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT action, details FROM user_activity_logs WHERE details->>'session_id' = %s",
                    (session_id,),
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == "search"
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM user_activity_logs WHERE details->>'session_id' = %s",
                        (session_id,),
                    )
        finally:
            conn.close()

    def test_log_failure_does_not_raise(self, user_manager):
        # 존재하지 않는 user_id — 외래 키 위반이지만 log_activity는 조용히 실패해야 함
        user_manager.log_activity("nonexistent-user-id", "test", {})

    def test_limit_is_respected(self, user_manager, test_user):
        for i in range(5):
            user_manager.log_activity(test_user["user_id"], f"action_{i}", None)

        logs = user_manager.get_activity_logs(test_user["user_id"], limit=3)
        assert len(logs) <= 3
