"""
Utility functions for API endpoints.
"""
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from fastapi import Request
import logging

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import get_firebase_manager
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    get_firebase_manager = None

logger = logging.getLogger(__name__)


def get_current_user_from_cookies(request: Request) -> Optional[Dict[str, Any]]:
    """쿠키에서 현재 사용자 정보 가져오기"""
    if not FIREBASE_AVAILABLE or get_firebase_manager is None:
        logger.debug("Firebase가 사용 불가능합니다.")
        return None
    
    try:
        # 모든 쿠키 확인
        all_cookies = dict(request.cookies)
        logger.info(f"모든 쿠키: {list(all_cookies.keys())}")
        
        auth_token = request.cookies.get("auth_token")
        user_uid = request.cookies.get("user_uid")
        
        logger.info(f"쿠키 확인 - auth_token: {auth_token is not None}, user_uid: {user_uid is not None}")
        if auth_token:
            logger.info(f"auth_token 값: {auth_token[:30]}...")
        if user_uid:
            logger.info(f"user_uid 값: {user_uid}")
        
        if not auth_token or not user_uid:
            logger.info("쿠키에 인증 정보가 없습니다.")
            return None
        
        if not auth_token.startswith("demo_token_"):
            logger.warning(f"잘못된 auth_token 형식: {auth_token[:20]}...")
            return None
        
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            logger.warning("Firebase가 초기화되지 않았습니다.")
            return None
        
        db = firebase_manager.get_firestore()
        user_doc = db.collection("users").document(user_uid).get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            logger.info(f"✅ 사용자 정보 로드 성공: {user_data.get('email', 'N/A')} (UID: {user_uid})")
            return user_data
        else:
            # 기본 사용자 정보 (Firestore에 없어도 쿠키가 있으면 로그인된 것으로 간주)
            logger.info(f"⚠️ Firestore에 사용자 문서가 없지만 쿠키가 있으므로 기본 정보 반환: {user_uid}")
            # 실제 이메일 정보를 가져오기 위해 auth에서 확인
            try:
                auth = firebase_manager.get_auth()
                user_record = auth.get_user(user_uid)
                return {
                    "uid": user_uid,
                    "email": user_record.email or "user@example.com",
                    "display_name": user_record.display_name or user_record.email.split("@")[0] if user_record.email else "User"
                }
            except Exception as e:
                logger.warning(f"Auth에서 사용자 정보 가져오기 실패: {e}")
                return {
                    "uid": user_uid,
                    "email": "user@example.com",
                    "display_name": "User"
                }
    except Exception as e:
        logger.error(f"쿠키에서 사용자 정보 가져오기 실패: {e}", exc_info=True)
        return None


def _safe_number(value) -> Optional[float]:
    """Convert numpy/NaN values to native floats."""
    if value is None:
        return None
    if isinstance(value, (float, int)):
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
        return float(value)
    if isinstance(value, (np.integer, np.floating)):
        if np.isnan(value):
            return None
        return float(value)
    return None


def _safe_year(value) -> Optional[int]:
    number = _safe_number(value)
    if number is None:
        return None
    return int(number)


def from_dataframe(
    df: pd.DataFrame,
    *,
    include_rating: bool = False,
    include_predicted: bool = False,
    include_similarity: bool = False,
) -> List[dict]:
    """Convert pandas DataFrame to list of dictionaries for API responses."""
    if df is None or df.empty:
        return []

    records = []
    for row in df.to_dict(orient="records"):
        # total_title이 있으면 우선 사용, 없으면 title 또는 movie_title 사용
        title = row.get("total_title") or row.get("title") or row.get("movie_title")
        record = {
            "movie_id": str(row.get("movie_id", "")),
            "title": title,
            "total_title": row.get("total_title"),  # total_title도 포함
            "genre": row.get("genre"),
            "year": _safe_year(row.get("year")),
        }
        
        # TMDB 관련 필드 추가
        genres_tmdb = row.get("genres_tmdb")
        if genres_tmdb and pd.notna(genres_tmdb):
            record["genres_tmdb"] = str(genres_tmdb)
        else:
            record["genres_tmdb"] = None
        
        record["vote_average"] = _safe_number(row.get("vote_average"))
        record["vote_count"] = _safe_number(row.get("vote_count"))
        record["release_date"] = row.get("release_date") if pd.notna(row.get("release_date")) else None
        record["overview"] = row.get("overview") if pd.notna(row.get("overview")) else None
        
        # 언어 필드 추가
        language = row.get("language")
        if language and pd.notna(language):
            record["language"] = str(language)
        else:
            record["language"] = None
        
        # 포스터 경로 (poster_path 우선, 없으면 backdrop_path)
        poster_path = row.get("poster_path") or row.get("backdrop_path")
        if poster_path and pd.notna(poster_path) and str(poster_path).strip():
            poster_path_str = str(poster_path).strip()
            # 슬래시가 없으면 추가
            if not poster_path_str.startswith('/'):
                poster_path_str = '/' + poster_path_str
            record["poster_path"] = poster_path_str
            record["poster_url"] = f"https://image.tmdb.org/t/p/w500{poster_path_str}"
        else:
            record["poster_path"] = None
            record["poster_url"] = None
        
        # adult 필드
        adult = row.get("adult")
        if adult is not None:
            record["adult"] = bool(adult) if not isinstance(adult, bool) else adult
        else:
            record["adult"] = False
        
        if include_rating:
            record["rating"] = _safe_number(row.get("rating"))
        if include_predicted:
            record["predicted_rating"] = _safe_number(row.get("predicted_rating"))
        if include_similarity:
            record["similarity"] = _safe_number(row.get("similarity"))
        records.append(record)
    return records

