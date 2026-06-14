"""
PostgreSQL 기반 사용자 관리 및 활동 로그
"""

import binascii
import hashlib
import json
import logging
import os
import secrets
import uuid
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    is_active    BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS user_activity_logs (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action     TEXT NOT NULL,
    details    JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON user_activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON user_activity_logs(created_at DESC);
"""


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "movie_recommendation"),
        user=os.environ.get("POSTGRES_USER", "movie_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "movie_pass"),
    )


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{binascii.hexlify(key).decode()}"


def _verify_password(stored_hash: str, password: str) -> bool:
    try:
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return binascii.hexlify(key).decode() == key_hex
    except Exception:
        return False


class UserManager:
    """사용자 CRUD + 활동 로그"""

    def __init__(self):
        self._ensure_schema()

    def _ensure_schema(self):
        try:
            conn = _connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(DDL)
            conn.close()
        except Exception as e:
            logger.error(f"스키마 초기화 실패: {e}")

    def create_user(self, email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """회원가입. 중복 이메일이면 ValueError 발생."""
        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password)
        display = display_name or email.split("@")[0]

        conn = _connect()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO users (user_id, email, display_name, password_hash)
                        VALUES (%s, %s, %s, %s)
                        RETURNING user_id, email, display_name, created_at, is_active
                        """,
                        (user_id, email, display, password_hash),
                    )
                    row = dict(cur.fetchone())
            self.log_activity(user_id, "signup", {"email": email})
            return row
        except psycopg2.errors.UniqueViolation:
            raise ValueError("이미 존재하는 이메일입니다.")
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = _connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, email, display_name, created_at, is_active FROM users WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = _connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, email, display_name, created_at, is_active FROM users WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def verify_credentials(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """이메일/비밀번호 검증. 성공하면 사용자 dict, 실패하면 None."""
        conn = _connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, email, display_name, password_hash, is_active FROM users WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                row = dict(row)
                if not _verify_password(row["password_hash"], password):
                    return None
                if not row["is_active"]:
                    return None
                row.pop("password_hash")
                return row
        finally:
            conn.close()

    def log_activity(self, user_id: str, action: str, details: Optional[Dict] = None):
        """사용자 활동 로그 기록"""
        try:
            conn = _connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO user_activity_logs (user_id, action, details) VALUES (%s, %s, %s)",
                        (user_id, action, json.dumps(details) if details else None),
                    )
            conn.close()
        except Exception as e:
            logger.warning(f"활동 로그 기록 실패 (무시): {e}")

    def get_user_ratings(self, user_id: str) -> List[Dict[str, Any]]:
        """custom_ratings 테이블에서 사용자 평점 조회"""
        conn = _connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT movie_id, title, rating FROM custom_ratings WHERE user_id = %s ORDER BY movie_id",
                    (user_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def add_user_rating(self, user_id: str, movie_id: str, title: Optional[str], rating: float) -> bool:
        """custom_ratings에 평점 추가/업데이트"""
        if not (0.5 <= rating <= 5.0):
            raise ValueError("평점은 0.5 ~ 5.0 사이여야 합니다.")
        try:
            conn = _connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO custom_ratings (user_id, movie_id, title, rating)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, movie_id) DO UPDATE SET rating = EXCLUDED.rating, title = EXCLUDED.title
                        """,
                        (user_id, movie_id, title, rating),
                    )
            conn.close()
            self.log_activity(user_id, "rate_movie", {"movie_id": movie_id, "rating": rating})
            return True
        except Exception as e:
            logger.error(f"평점 저장 실패: {e}")
            return False

    def get_activity_logs(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        conn = _connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT action, details, created_at
                    FROM user_activity_logs WHERE user_id = %s
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (user_id, limit),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()


_instance: Optional[UserManager] = None


def get_user_manager() -> UserManager:
    global _instance
    if _instance is None:
        _instance = UserManager()
    return _instance
