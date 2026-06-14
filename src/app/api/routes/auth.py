"""
Authentication API endpoints.
- 회원가입 / 로그인 / 로그아웃
- PostgreSQL users 테이블 사용
"""

import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from core.user_system.db_manager import get_user_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    display_name: Optional[str] = Form(None),
):
    """회원가입"""
    try:
        user = get_user_manager().create_user(email, password, display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")

    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.set_cookie(key="auth_token", value=f"token_{user['user_id']}", max_age=86400 * 7, httponly=True, samesite="lax", path="/")
    response.set_cookie(key="user_uid", value=user["user_id"], max_age=86400 * 7, httponly=True, samesite="lax", path="/")
    logger.info(f"회원가입 성공: {user['email']} ({user['user_id']})")
    return response


@router.post("/auth/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
):
    """로그인"""
    if not password or not password.strip():
        error_msg = "비밀번호를 입력해주세요."
        return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

    user = get_user_manager().verify_credentials(email, password)
    if not user:
        error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
        return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

    get_user_manager().log_activity(user["user_id"], "login", {"email": email})

    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.set_cookie(key="auth_token", value=f"token_{user['user_id']}", max_age=86400 * 7, httponly=True, samesite="lax", path="/")
    response.set_cookie(key="user_uid", value=user["user_id"], max_age=86400 * 7, httponly=True, samesite="lax", path="/")
    logger.info(f"로그인 성공: {user['email']} ({user['user_id']})")
    return response


@router.post("/auth/logout")
async def logout():
    """로그아웃"""
    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.delete_cookie("auth_token")
    response.delete_cookie("user_uid")
    return response
