"""
Authentication API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import RedirectResponse
import pandas as pd

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import get_firebase_manager
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

router = APIRouter()


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
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name or email.split("@")[0]
        )
        
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
        response = RedirectResponse(url="/?page=movie_based", status_code=303)
        response.set_cookie(
            key="auth_token",
            value=f"demo_token_{user_record.uid}",
            max_age=86400 * 7,  # 7일
            httponly=True,
        )
        response.set_cookie(
            key="user_uid",
            value=user_record.uid,
            max_age=86400 * 7,
            httponly=True,
        )
        
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
    """로그인"""
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Firebase가 사용 불가능합니다.")
    
    try:
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            raise HTTPException(status_code=503, detail="Firebase가 초기화되지 않았습니다.")
        
        auth = firebase_manager.get_auth()
        
        # 사용자 확인 (비밀번호 검증은 Firebase Web SDK에서만 가능)
        # 여기서는 사용자 존재 여부만 확인
        try:
            user_record = auth.get_user_by_email(email)
        except Exception:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        
        # 응답에 쿠키 설정
        response = RedirectResponse(url="/?page=movie_based", status_code=303)
        response.set_cookie(
            key="auth_token",
            value=f"demo_token_{user_record.uid}",
            max_age=86400 * 7,  # 7일
            httponly=True,
        )
        response.set_cookie(
            key="user_uid",
            value=user_record.uid,
            max_age=86400 * 7,
            httponly=True,
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")


@router.post("/auth/logout")
async def logout():
    """로그아웃"""
    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.delete_cookie("auth_token")
    response.delete_cookie("user_uid")
    return response

