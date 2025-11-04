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
import yaml

from modules.services.data_access import load_all_data, search_movies_cached, get_data_stats
from modules.services.recommender_service import (
    get_recommender_service,
    recommend_for_user as recommend_for_user_func,
    similar_movies as similar_movies_func,
)
from app.api.utils import get_current_user_from_cookies, from_dataframe, _safe_year
from app.api.app_state import get_loading_state

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
    user_top_n: int = Query(10, ge=5, le=20),
    user_option: Optional[str] = Query(None, description="사용자 선택 옵션: me 또는 other"),
    movie_search_query: Optional[str] = Query(None, description="영화 검색 쿼리"),
    selected_movie_id: Optional[str] = Query(None, description="선택된 영화 ID"),
    similar_top_n: int = Query(10, ge=5, le=15),
    movie_genre: Optional[List[str]] = Query(None, description="장르 필터"),
    movie_language: Optional[List[str]] = Query(None, description="언어 필터"),
    rating_method: Optional[str] = Query("search", description="평점 입력 방식"),
    rating_movie_id: Optional[str] = Query(None, description="평점 입력할 영화 ID"),
    rating_value: Optional[float] = Query(None, ge=0.5, le=5.0, description="평점 값"),
    explore_count: int = Query(10, ge=5, le=20, description="탐색할 영화 개수"),
):
    """Render a simple HTML frontend for interacting with the recommender."""
    # 로딩 상태 확인
    loading_state = get_loading_state()
    if loading_state["is_loading"]:
        return templates.TemplateResponse(
            "loading.html",
            {
                "request": request,
                "loading_message": loading_state["loading_message"],
                "progress": loading_state["progress"],
            }
        )
    
    import time
    request_start = time.time()
    
    errors: List[str] = []
    
    # 기본 페이지는 movie_based
    current_page = page or "movie_based"

    # 영화 기반 추천용 검색 결과
    movie_search_results = []
    selected_movie_info = None

    # 모델 로드 상태 확인 (사이드바 표시용)
    # 캐시되어 있으므로 빠르게 반환됨
    model_load_start = time.time()
    model_loaded = False
    recommender_service = None
    try:
        # 이미 로드되어 있으면 로그 없이 빠르게 반환
        recommender_service = get_recommender_service()
        model_loaded = True
        logger.debug(f"모델 서비스 가져오기: {time.time() - model_load_start:.3f}초")
    except FileNotFoundError as exc:
        logger.warning(f"⚠️ 모델 파일을 찾을 수 없습니다: {exc}")
        errors.append(str(exc))
    except Exception as exc:
        logger.error(f"❌ 모델 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)
        errors.append(f"모델 로드 중 오류가 발생했습니다: {str(exc)}")

    df_movies = None
    df_ratings = None
    
    # 통계 정보는 캐시된 함수 사용 (사이드바 통계용)
    stats_start = time.time()
    try:
        stats = get_data_stats()
        logger.debug(f"통계 정보 로드: {time.time() - stats_start:.3f}초")
    except Exception as exc:
        logger.error(f"통계 정보 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)
        stats = {
            "total_movies": "0",
            "total_ratings": "0",
            "total_users": "0",
            "avg_rating": None,
        }
    
    # 실제 데이터는 필요한 경우에만 로드 (지연 로딩)
    data_load_start = time.time()
    try:
        # 현재 페이지에 따라 필요한 데이터만 로드
        # 영화 기반: 검색이나 선택된 영화가 있을 때
        # 사용자 기반: 사용자 ID가 있을 때
        # 평점 관리: 항상 필요
        needs_full_data = (
            (current_page == "movie_based" and (selected_movie_id or movie_search_query)) or
            (current_page == "user_based" and (user_id or user_option == "me")) or
            current_page == "rating_management"
        )
        
        if needs_full_data:
            logger.info(f"데이터 로드 시작... (페이지: {current_page})")
            df_movies, df_ratings, _ = load_all_data()
            logger.info(f"✅ 데이터 로드 완료: {time.time() - data_load_start:.3f}초")
        else:
            logger.debug(f"데이터 로드 스킵 (필요 없음, 페이지: {current_page})")
    except FileNotFoundError as exc:
        logger.warning(f"데이터 파일을 찾을 수 없습니다: {exc}")
    except Exception as exc:
        logger.error(f"데이터 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)

    # 영화 기반 추천: 영화 검색 및 선택
    if current_page == "movie_based" and df_movies is not None:
        if movie_search_query and movie_search_query.strip():
            try:
                df_search = search_movies_cached(query=movie_search_query, limit=10)
                movie_search_results = from_dataframe(df_search)
            except Exception as e:
                logger.error(f"영화 검색 실패: {e}", exc_info=True)
        
        # 선택된 영화 정보 가져오기
        if selected_movie_id and df_movies is not None:
            try:
                movie_row = df_movies[df_movies["movie_id"] == selected_movie_id]
                if not movie_row.empty:
                    selected_movie_info = from_dataframe(movie_row.head(1))[0]
            except Exception as e:
                logger.error(f"영화 정보 조회 실패: {e}", exc_info=True)

    # User recommendations
    user_recommendations = None
    # 사용자 기반 추천: 로그인된 사용자 또는 선택된 사용자
    if current_page == "user_based":
        # 로그인된 사용자 선택 옵션
        if user_option == "me" and is_logged_in and current_user:
            user_id = current_user.get("uid")
        
        if user_id and recommender_service is not None and df_ratings is not None:
            if user_id not in df_ratings["user_id"].values:
                # Firebase 사용자일 경우 데이터 없을 수 있음
                if user_option == "me":
                    errors.append("아직 학습되기 전입니다. 더 많은 평점을 입력해주세요.")
                else:
                    errors.append(f"사용자 '{user_id}'를 평점 데이터에서 찾을 수 없습니다.")
            else:
                try:
                    top_watched_df, recommendations_df = recommend_for_user_func(
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

    # Similar movies (영화 기반 추천 결과)
    similar_movies = None
    if selected_movie_id and recommender_service is not None and df_movies is not None:
        if selected_movie_id not in df_movies["movie_id"].values:
            errors.append(f"영화 ID '{selected_movie_id}'를 영화 데이터에서 찾을 수 없습니다.")
        else:
            try:
                # 필터 구성
                filters = {}
                if movie_genre:
                    filters["genre"] = movie_genre
                if movie_language:
                    filters["language"] = movie_language
                
                similar_df = similar_movies_func(
                    movie_id=selected_movie_id,
                    df_movies=df_movies,
                    n_recommendations=similar_top_n,
                    filters=filters if filters else None,
                )
                similar_movies = {
                    "movie_id": selected_movie_id,
                    "items": from_dataframe(similar_df, include_similarity=True),
                }
            except ValueError as exc:
                errors.append(str(exc))
    
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
    
    # 설정값 로드 (장르, 국가, 연도 옵션)
    config_path = BASE_DIR / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config_options = yaml.safe_load(f)
    
    # 사용 가능한 사용자 목록 (사용자 기반 추천용)
    available_users = []
    if current_page == "user_based" and df_ratings is not None:
        try:
            available_users = sorted(df_ratings["user_id"].unique().tolist()[:100])
        except Exception:
            pass
    
    context = {
        "request": request,
        "title": "볼거 없나? 추천 서비스",
        "current_page": current_page,
        "search_query": query or "",
        "search_limit": limit,
        "movie_search_query": movie_search_query or "",
        "movie_search_results": movie_search_results,
        "selected_movie_id": selected_movie_id or "",
        "selected_movie_info": selected_movie_info,
        "rating_search_results": rating_search_results,
        "user_id": user_id or "",
        "user_option": user_option or "",
        "user_top_n": user_top_n,
        "user_recommendations": user_recommendations,
        "available_users": available_users,
        "similar_top_n": similar_top_n,
        "similar_movies": similar_movies,
        "movie_genre": movie_genre or [],
        "movie_language": movie_language or [],
        "config_options": config_options,
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

    total_time = time.time() - request_start
    logger.info(f"✅ 전체 요청 처리 완료: {total_time:.3f}초 (페이지: {current_page})")
    
    return templates.TemplateResponse("index.html", context)

