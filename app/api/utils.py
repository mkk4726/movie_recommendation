"""
Utility functions for API endpoints.
"""
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from fastapi import Request
import logging

from app.api.models import MovieCastInfo, CastMember

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


def get_movie_cast_info(imdb_id: str, cast_df: pd.DataFrame) -> Optional[MovieCastInfo]:
    """
    특정 영화의 출연진 및 제작진 정보를 가져옵니다.
    
    Args:
        imdb_id: 영화 IMDB ID
        cast_df: Cast 데이터프레임
    
    Returns:
        MovieCastInfo 객체 또는 None
    """
    if cast_df is None or cast_df.empty or imdb_id is None or pd.isna(imdb_id):
        return None
    
    # 해당 영화의 cast 데이터 필터링
    movie_cast = cast_df[cast_df['imdb_id'] == imdb_id]
    
    if movie_cast.empty:
        return None
    
    # 배우 정보 (Acting, cast_id로 정렬, 상위 5명)
    actors_data = movie_cast[movie_cast['known_for_department'] == 'Acting'].sort_values('cast_id').head(5)
    actors = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=row['character'] if pd.notna(row['character']) else None,
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in actors_data.iterrows()
    ]
    
    # 감독 정보 (Directing, cast_id로 정렬)
    directors_data = movie_cast[movie_cast['known_for_department'] == 'Directing'].sort_values('cast_id')
    directors = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=None,  # 감독은 character 없음
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in directors_data.iterrows()
    ]
    
    # 작가 정보 (Writing, cast_id로 정렬)
    writers_data = movie_cast[movie_cast['known_for_department'] == 'Writing'].sort_values('cast_id')
    writers = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=None,  # 작가는 character 없음
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in writers_data.iterrows()
    ]
    
    return MovieCastInfo(actors=actors, directors=directors, writers=writers)


def add_cast_info_to_results(
    results: List[dict],
    cast_df: Optional[pd.DataFrame] = None
) -> List[dict]:
    """
    검색/추천 결과에 cast 정보를 추가합니다.
    
    Args:
        results: 영화 결과 리스트
        cast_df: Cast 데이터프레임 (None이면 cast 정보 추가 안함)
    
    Returns:
        Cast 정보가 추가된 결과 리스트
    """
    if cast_df is None or cast_df.empty:
        return results
    
    for result in results:
        imdb_id = result.get('imdb_id')
        if imdb_id:
            cast_info = get_movie_cast_info(imdb_id, cast_df)
            if cast_info:
                # Pydantic 모델을 딕셔너리로 변환 (Jinja2 템플릿에서 사용 가능하도록)
                result['cast_info'] = {
                    'actors': [
                        {
                            'name': actor.name,
                            'original_name': actor.original_name,
                            'character': actor.character,
                            'profile_path': actor.profile_path
                        }
                        for actor in cast_info.actors
                    ],
                    'directors': [
                        {
                            'name': director.name,
                            'original_name': director.original_name,
                            'character': director.character,
                            'profile_path': director.profile_path
                        }
                        for director in cast_info.directors
                    ],
                    'writers': [
                        {
                            'name': writer.name,
                            'original_name': writer.original_name,
                            'character': writer.character,
                            'profile_path': writer.profile_path
                        }
                        for writer in cast_info.writers
                    ]
                }
    
    return results


def from_dataframe(
    df: pd.DataFrame,
    *,
    include_rating: bool = False,
    include_predicted: bool = False,
    include_similarity: bool = False,
    cast_df: Optional[pd.DataFrame] = None,
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
            "imdb_id": row.get("imdb_id") if pd.notna(row.get("imdb_id")) else None,
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
    
    # Cast 정보 추가 (옵션)
    if cast_df is not None:
        records = add_cast_info_to_results(records, cast_df)
    
    return records

