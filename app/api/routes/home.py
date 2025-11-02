"""
Home page route for rendering the HTML frontend.
"""
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd

from modules.services.data_access import load_all_data, search_movies_cached
from modules.services.recommender_service import get_recommender_service
from app.api.utils import get_current_user_from_cookies, from_dataframe, _safe_year

logger = logging.getLogger(__name__)

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import get_firebase_manager
    from user_system.firebase_firestore import FirestoreManager
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    page: Optional[str] = Query("movie_based", description="페이지 타입"),
    query: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=50),
    user_id: Optional[str] = Query(None),
    user_top_n: int = Query(5, ge=1, le=20),
    movie_id: Optional[str] = Query(None),
    similar_top_n: int = Query(5, ge=1, le=20),
    rating_method: Optional[str] = Query("search", description="평점 입력 방식"),
    rating_movie_id: Optional[str] = Query(None, description="평점 입력할 영화 ID"),
    rating_value: Optional[float] = Query(None, ge=0.5, le=5.0, description="평점 값"),
    explore_count: int = Query(10, ge=5, le=20, description="탐색할 영화 개수"),
):
    """Render a simple HTML frontend for interacting with the recommender."""
    errors: List[str] = []

    # Search movies (영화 검색 페이지가 제거되어 더 이상 사용하지 않음)
    search_results = []

    # 모델 로드 상태 확인 (사이드바 표시용)
    # 캐시되어 있으므로 빠르게 반환됨
    model_loaded = False
    recommender_service = None
    try:
        # 이미 로드되어 있으면 로그 없이 빠르게 반환
        recommender_service = get_recommender_service()
        model_loaded = True
    except FileNotFoundError as exc:
        logger.warning(f"⚠️ 모델 파일을 찾을 수 없습니다: {exc}")
        errors.append(str(exc))
    except Exception as exc:
        logger.error(f"❌ 모델 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)
        errors.append(f"모델 로드 중 오류가 발생했습니다: {str(exc)}")

    df_movies = None
    df_ratings = None
    stats = {
        "total_movies": "0",
        "total_ratings": "0",
        "total_users": "0",
        "avg_rating": None,
    }
    
    # 데이터 로드 시도 (사이드바 통계용)
    try:
        logger.debug("데이터 로드 시도 중...")
        df_movies, df_ratings, _ = load_all_data()
        if df_movies is not None and df_ratings is not None:
            stats = {
                "total_movies": f"{len(df_movies):,}",
                "total_ratings": f"{len(df_ratings):,}",
                "total_users": f"{df_ratings['user_id'].nunique():,}" if "user_id" in df_ratings.columns else "0",
                "avg_rating": float(df_ratings["rating"].mean()) if "rating" in df_ratings.columns else None,
            }
            logger.debug(f"데이터 로드 완료: 영화 {stats['total_movies']}개, 평점 {stats['total_ratings']}개")
    except FileNotFoundError as exc:
        logger.warning(f"데이터 파일을 찾을 수 없습니다: {exc}")
    except Exception as exc:
        logger.error(f"데이터 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)

    # User recommendations
    user_recommendations = None
    if user_id and recommender_service is not None and df_ratings is not None:
        if user_id not in df_ratings["user_id"].values:
            errors.append(f"사용자 '{user_id}'를 평점 데이터에서 찾을 수 없습니다.")
        else:
            try:
                top_watched_df, recommendations_df = recommender_service.recommend_for_user(
                    user_id=user_id,
                    df_movies=df_movies,
                    n=user_top_n,
                )
                user_recommendations = {
                    "user_id": user_id,
                    "top_watched": from_dataframe(top_watched_df, include_rating=True),
                    "recommendations": from_dataframe(recommendations_df, include_predicted=True),
                }
            except ValueError as exc:
                errors.append(str(exc))

    # Similar movies
    similar_movies = None
    if movie_id and recommender_service is not None and df_movies is not None:
        if movie_id not in df_movies["movie_id"].values:
            errors.append(f"영화 ID '{movie_id}'를 영화 데이터에서 찾을 수 없습니다.")
        else:
            try:
                similar_df = recommender_service.similar_movies(
                    movie_id=movie_id,
                    df_movies=df_movies,
                    n_recommendations=similar_top_n,
                    filters=None,
                )
                similar_movies = {
                    "movie_id": movie_id,
                    "items": from_dataframe(similar_df, include_similarity=True),
                }
            except ValueError as exc:
                errors.append(str(exc))

    # 기본 페이지는 movie_based
    current_page = page or "movie_based"
    
    # 현재 사용자 정보 가져오기
    current_user = get_current_user_from_cookies(request)
    if FIREBASE_AVAILABLE:
        try:
            firebase_available = get_firebase_manager().initialized
        except:
            firebase_available = False
    else:
        firebase_available = False
    is_logged_in = current_user is not None
    
    # 평점 관리 페이지 데이터 로드
    rating_search_results = []
    user_ratings_list = []
    rating_stats = {
        "total": 0,
        "avg": 0.0,
        "high": 0,
        "low": 0,
    }
    if current_page == "rating_management" and is_logged_in and firebase_available:
        try:
            # 영화 검색 결과 (평점 입력용)
            if query:
                df_search = search_movies_cached(query=query, limit=limit)
                rating_search_results = from_dataframe(df_search)
            
            # 사용자 평점 목록
            firestore_manager = FirestoreManager()
            user_uid = current_user.get("uid")
            if user_uid:
                user_ratings_df = firestore_manager.get_user_ratings(user_uid)
                if not user_ratings_df.empty:
                    # 영화 정보와 병합
                    for _, rating_row in user_ratings_df.iterrows():
                        movie_id = str(rating_row.get("movie_id", ""))
                        rating = rating_row.get("rating", 0)
                        movie_row = df_movies[df_movies["movie_id"] == movie_id] if df_movies is not None else pd.DataFrame()
                        if not movie_row.empty:
                            movie_data = movie_row.iloc[0]
                            user_ratings_list.append({
                                "movie_id": movie_id,
                                "title": movie_data.get("title") or movie_data.get("movie_title", "N/A"),
                                "year": _safe_year(movie_data.get("year")),
                                "genre": movie_data.get("genre"),
                                "rating": rating,
                                "created_at": rating_row.get("created_at", ""),
                            })
                    
                    # 평점 통계
                    ratings_list = user_ratings_df["rating"].tolist()
                    rating_stats = {
                        "total": len(ratings_list),
                        "avg": sum(ratings_list) / len(ratings_list) if ratings_list else 0,
                        "high": len([r for r in ratings_list if r >= 4.0]),
                        "low": len([r for r in ratings_list if r <= 2.0]),
                    }
        except Exception as e:
            errors.append(f"평점 데이터 로드 실패: {str(e)}")
    
    context = {
        "request": request,
        "title": "볼거 없나? 추천 서비스",
        "current_page": current_page,
        "search_query": query or "",
        "search_limit": limit,
        "search_results": search_results,
        "rating_search_results": rating_search_results,
        "user_id": user_id or "",
        "user_top_n": user_top_n,
        "user_recommendations": user_recommendations,
        "movie_id": movie_id or "",
        "similar_top_n": similar_top_n,
        "similar_movies": similar_movies,
        "errors": errors,
        "stats": stats,
        "model_loaded": model_loaded,
        "firebase_available": firebase_available,
        "is_logged_in": is_logged_in,
        "current_user": current_user,
        "rating_method": rating_method or "search",
        "rating_movie_id": rating_movie_id or "",
        "user_ratings_list": user_ratings_list,
        "rating_stats": rating_stats,
        "explore_count": explore_count,
    }

    return templates.TemplateResponse("index.html", context)

