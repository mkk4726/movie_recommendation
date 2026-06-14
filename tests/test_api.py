"""
FastAPI 엔드포인트 통합 테스트

실제 DB + FastAPI TestClient를 사용합니다.
ML 모델 로딩은 lifespan 백그라운드 태스크로 분리되어 있어
auth/ratings 엔드포인트 테스트에 영향을 주지 않습니다.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from core.user_system.db_manager import _connect, get_user_manager


@pytest.fixture(scope="module")
def client():
    from app.api.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def fresh_email():
    return f"apitest_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def registered_user(client, fresh_email):
    """TestClient로 회원가입한 사용자 + 자동 정리"""
    resp = client.post(
        "/auth/signup",
        data={"email": fresh_email, "password": "pass1234", "display_name": "API Tester"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    yield {"email": fresh_email, "password": "pass1234", "cookies": dict(resp.cookies)}
    # 정리
    user = get_user_manager().get_user_by_email(fresh_email)
    if user:
        conn = _connect()
        with conn:
            conn.cursor().execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
        conn.close()


# ─── 회원가입 ───────────────────────────────────────────────────────────────

class TestSignup:
    def test_signup_redirects_on_success(self, client, fresh_email):
        resp = client.post(
            "/auth/signup",
            data={"email": fresh_email, "password": "pass1234"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "movie_based" in resp.headers["location"]
        # 쿠키 설정 확인
        assert "user_uid" in resp.cookies
        assert "auth_token" in resp.cookies
        # 정리
        user = get_user_manager().get_user_by_email(fresh_email)
        if user:
            conn = _connect()
            with conn:
                conn.cursor().execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
            conn.close()

    def test_signup_stores_user_in_db(self, registered_user):
        user = get_user_manager().get_user_by_email(registered_user["email"])
        assert user is not None
        assert user["email"] == registered_user["email"]

    def test_duplicate_signup_raises_400(self, client, registered_user):
        resp = client.post(
            "/auth/signup",
            data={"email": registered_user["email"], "password": "other"},
            follow_redirects=False,
        )
        assert resp.status_code == 400


# ─── 로그인 ─────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success_sets_cookies(self, client, registered_user):
        resp = client.post(
            "/auth/login",
            data={"email": registered_user["email"], "password": registered_user["password"]},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "user_uid" in resp.cookies
        assert "auth_token" in resp.cookies

    def test_login_wrong_password_redirects_with_error(self, client, registered_user):
        resp = client.post(
            "/auth/login",
            data={"email": registered_user["email"], "password": "wrong"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "auth_error" in resp.headers["location"]

    def test_login_unknown_email_redirects_with_error(self, client):
        resp = client.post(
            "/auth/login",
            data={"email": "ghost@nowhere.com", "password": "any"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "auth_error" in resp.headers["location"]

    def test_login_empty_password_redirects_with_error(self, client, registered_user):
        resp = client.post(
            "/auth/login",
            data={"email": registered_user["email"], "password": "   "},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "auth_error" in resp.headers["location"]


# ─── 로그아웃 ────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_cookies(self, client, registered_user):
        # 먼저 로그인
        login_resp = client.post(
            "/auth/login",
            data={"email": registered_user["email"], "password": registered_user["password"]},
            follow_redirects=False,
        )
        assert "user_uid" in login_resp.cookies

        # 로그아웃
        logout_resp = client.post("/auth/logout", follow_redirects=False)
        assert logout_resp.status_code == 303
        # 쿠키가 삭제(빈 값)되어야 함
        assert logout_resp.cookies.get("user_uid", "") == ""


# ─── 평점 (인증 필요) ────────────────────────────────────────────────────────

class TestRatingEndpoints:
    def _logged_in_client(self, client, registered_user):
        """로그인된 세션을 가진 클라이언트 반환"""
        client.post(
            "/auth/login",
            data={"email": registered_user["email"], "password": registered_user["password"]},
            follow_redirects=False,
        )
        return client

    def test_add_rating_unauthenticated_returns_401(self, client):
        # 쿠키 없이 요청
        resp = client.post(
            "/rating/add",
            data={"movie_id": "tt0111161", "rating": 4.5},
        )
        assert resp.status_code == 401

    def test_add_rating_authenticated_redirects(self, client, registered_user):
        c = self._logged_in_client(client, registered_user)
        resp = c.post(
            "/rating/add",
            data={"movie_id": "tt0111161", "rating": 4.5},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_delete_rating_unauthenticated_returns_401(self, client):
        resp = client.post("/rating/delete", data={"movie_id": "tt0111161"})
        assert resp.status_code == 401
