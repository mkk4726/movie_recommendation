"""
공통 pytest fixtures
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

# src를 pythonpath에 추가 (pyproject.toml의 pythonpath 설정을 보완)
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "movie_recommendation")
os.environ.setdefault("POSTGRES_USER", "movie_user")
os.environ.setdefault("POSTGRES_PASSWORD", "movie_pass")


@pytest.fixture(scope="session")
def user_manager():
    from core.user_system.db_manager import get_user_manager
    return get_user_manager()


@pytest.fixture
def unique_email():
    """테스트마다 고유한 이메일 반환"""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user(user_manager, unique_email):
    """테스트용 사용자 생성 후 자동 정리"""
    user = user_manager.create_user(unique_email, "password123", "Test User")
    yield user
    # 정리
    try:
        from core.user_system.db_manager import _connect
        conn = _connect()
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s", (user["user_id"],))
        conn.close()
    except Exception:
        pass
