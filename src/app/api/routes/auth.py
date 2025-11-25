"""
Authentication API endpoints.
- 사용자 존재 여부 확인
- Firebase REST API를 사용한 비밀번호 검증
- 쿠키에 auth_token과 user_uid 저장
"""

import logging
import os
from typing import Optional
from urllib.parse import quote

import httpx
import pandas as pd
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import get_firebase_manager

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

router = APIRouter()


async def verify_password_with_firebase(email: str, password: str) -> bool:
    """
    Firebase REST API를 사용하여 비밀번호 검증

    Firebase Admin SDK는 비밀번호를 직접 검증할 수 없으므로
    REST API를 사용해야 합니다.

    Returns:
        True: 비밀번호 검증 성공
        False: 비밀번호 검증 실패 또는 API Key가 없음
    """
    try:
        # Firebase Web API Key를 환경변수에서 가져옴 (.env 파일에서)
        # FIREBASE_API_KEY 또는 FIREBASE_WEB_API_KEY 둘 다 지원
        api_key = os.getenv("FIREBASE_API_KEY") or os.getenv("FIREBASE_WEB_API_KEY")

        if not api_key:
            logger.warning(
                "FIREBASE_API_KEY 또는 FIREBASE_WEB_API_KEY가 설정되지 않았습니다. 비밀번호 검증을 건너뜁니다."
            )
            # API Key가 없으면 검증 실패로 처리 (보안상 안전)
            return False

        logger.info(f"Firebase API Key 로드 완료 (길이: {len(api_key)}, 시작: {api_key[:10]}...)")

        # Firebase REST API 엔드포인트
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {"email": email, "password": password, "returnSecureToken": True}

        logger.info(f"Firebase REST API 호출 시작: {email}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)

            logger.info(f"Firebase REST API 응답: status_code={response.status_code}")

            if response.status_code == 200:
                logger.info(f"✅ Firebase REST API 비밀번호 검증 성공: {email}")
                return True
            else:
                # 에러 응답 파싱
                try:
                    error_data = response.json()
                    error_info = error_data.get("error", {})
                    error_code = error_info.get("code", "unknown")
                    error_msg = error_info.get("message", "Unknown error")
                    logger.warning(f"❌ Firebase REST API 비밀번호 검증 실패: [{error_code}] {error_msg}")
                    logger.debug(f"전체 에러 응답: {error_data}")
                except Exception as parse_error:
                    logger.warning(f"Firebase REST API 응답 파싱 실패: {parse_error}")
                    logger.warning(f"응답 내용: {response.text[:200]}")
                return False

    except httpx.TimeoutException:
        logger.error("비밀번호 검증 타임아웃 (10초 초과)")
        return False
    except httpx.RequestError as e:
        logger.error(f"Firebase REST API 요청 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"비밀번호 검증 중 예상치 못한 오류: {e}", exc_info=True)
        return False


@router.post("/auth/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    display_name: Optional[str] = Form(None),
):
    """회원가입"""
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Firebase가 사용 불가능합니다.")

    try:
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            raise HTTPException(status_code=503, detail="Firebase가 초기화되지 않았습니다.")

        auth = firebase_manager.get_auth()
        db = firebase_manager.get_firestore()

        # 이메일 중복 체크
        try:
            auth.get_user_by_email(email)
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")
        except Exception:
            pass  # 사용자가 없으면 정상

        # 사용자 생성
        user_record = auth.create_user(email=email, password=password, display_name=display_name or email.split("@")[0])

        # Firestore에 사용자 프로필 생성
        user_data = {
            "uid": user_record.uid,
            "email": user_record.email,
            "display_name": user_record.display_name or email.split("@")[0],
            "created_at": pd.Timestamp.now().isoformat(),
            "is_active": True,
        }
        db.collection("users").document(user_record.uid).set(user_data)

        # 응답에 쿠키 설정
        auth_token_value = f"demo_token_{user_record.uid}"
        logger.info(f"회원가입 성공: {user_record.email} (UID: {user_record.uid})")
        logger.info(f"쿠키 설정 예정: auth_token={auth_token_value[:30]}..., user_uid={user_record.uid}")

        response = RedirectResponse(url="/?page=movie_based", status_code=303)
        response.set_cookie(
            key="auth_token",
            value=auth_token_value,
            max_age=86400 * 7,  # 7일
            httponly=True,
            samesite="lax",
            path="/",
            secure=False,  # localhost에서는 False
        )
        response.set_cookie(
            key="user_uid",
            value=user_record.uid,
            max_age=86400 * 7,
            httponly=True,
            samesite="lax",
            path="/",
            secure=False,  # localhost에서는 False
        )

        logger.info(f"쿠키 설정 완료: response.headers={dict(response.headers)}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")


@router.post("/auth/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
):
    """
    로그인
    - 사용자 존재 여부 확인
    - Firebase REST API를 사용한 비밀번호 검증
    """
    if not FIREBASE_AVAILABLE:
        error_msg = "Firebase가 사용 불가능합니다."
        return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

    # 비밀번호 입력 확인
    if not password or len(password.strip()) == 0:
        error_msg = "비밀번호를 입력해주세요."
        return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

    try:
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            error_msg = "Firebase가 초기화되지 않았습니다."
            return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

        auth = firebase_manager.get_auth()
        db = firebase_manager.get_firestore()

        # 사용자 존재 여부 확인
        try:
            user_record = auth.get_user_by_email(email)
        except Exception as e:
            error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
            logger.warning(f"사용자 조회 실패: {e}")
            return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

        # 비밀번호 검증 (Firebase REST API 사용)
        logger.info(f"비밀번호 검증 시작: {email}")
        password_valid = await verify_password_with_firebase(email, password)

        if not password_valid:
            error_msg = "이메일 또는 비밀번호가 올바르지 않습니다."
            logger.warning(f"비밀번호 검증 실패: {email}")
            return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)

        logger.info(f"비밀번호 검증 성공: {email}")

        # 사용자 프로필이 없으면 생성
        user_doc = db.collection("users").document(user_record.uid).get()
        if not user_doc.exists:
            user_data = {
                "uid": user_record.uid,
                "email": user_record.email,
                "display_name": user_record.display_name or email.split("@")[0],
                "created_at": pd.Timestamp.now().isoformat(),
                "is_active": True,
            }
            db.collection("users").document(user_record.uid).set(user_data)
            logger.info(f"사용자 프로필 생성: {user_record.uid}")

        # 쿠키 설정
        auth_token_value = f"demo_token_{user_record.uid}"
        logger.info(f"✅ 로그인 성공: {user_record.email} (UID: {user_record.uid})")
        logger.info(f"쿠키 설정 예정: auth_token={auth_token_value[:30]}..., user_uid={user_record.uid}")

        response = RedirectResponse(url="/?page=movie_based", status_code=303)
        response.set_cookie(
            key="auth_token",
            value=auth_token_value,
            max_age=86400 * 7,  # 7일
            httponly=True,
            samesite="lax",
            path="/",
            secure=False,  # localhost에서는 False
        )
        response.set_cookie(
            key="user_uid",
            value=user_record.uid,
            max_age=86400 * 7,
            httponly=True,
            samesite="lax",
            path="/",
            secure=False,  # localhost에서는 False
        )

        logger.info(f"쿠키 설정 완료: response.headers={dict(response.headers)}")
        return response

    except Exception as e:
        error_msg = f"로그인 실패: {str(e)}"
        logger.error(f"로그인 예외 발생: {e}", exc_info=True)
        return RedirectResponse(url=f"/?page=movie_based&auth_error={quote(error_msg)}", status_code=303)


@router.post("/auth/logout")
async def logout():
    """로그아웃"""
    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.delete_cookie("auth_token")
    response.delete_cookie("user_uid")
    return response
