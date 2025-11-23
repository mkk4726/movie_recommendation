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

from modules.services.data_access import load_all_data, search_movies_cached, get_data_stats, load_cast_data
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
    page: Optional[str] = Query("search", description="페이지 타입"),
    query: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    user_top_n: int = Query(10, ge=5, le=20),
    user_option: Optional[str] = Query(None, description="사용자 선택 옵션: me 또는 other"),
    movie_search_query: Optional[str] = Query(None, description="영화 검색 쿼리"),
    selected_movie_id: Optional[str] = Query(None, description="선택된 영화 ID"),
    similar_top_n: int = Query(10, ge=5, le=15),
    movie_genre: Optional[List[str]] = Query(None, description="장르 필터"),
    movie_language: Optional[List[str]] = Query(None, description="언어 필터"),
    search_query: Optional[str] = Query(None, description="자연어 검색 쿼리"),
    poster_query: Optional[str] = Query(None, description="포스터 검색 쿼리"),
    rating_method: Optional[str] = Query("search", description="평점 입력 방식"),                                                                               
    rating_movie_id: Optional[str] = Query(None, description="평점 입력할 영화 ID"),                                                                            
    rating_value: Optional[float] = Query(None, ge=0.5, le=5.0, description="평점 값"),                                                                        
    selected_rating_movie_id: Optional[str] = Query(None, description="평점 관리에서 선택된 영화 ID"),                                                                        
    explore_count: int = Query(10, ge=5, le=20, description="탐색할 영화 개수"),
    explored_movie_ids: Optional[str] = Query(None, description="탐색된 영화 ID들 (쉼표로 구분)"),
    auth_error: Optional[str] = Query(None, description="인증 에러 메시지"),
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
    
    # 인증 에러 메시지 추가
    if auth_error:
        errors.append(auth_error)
    
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
    
    # Cast 데이터 로드 (캐시됨, 한 번만 로드)
    try:
        cast_df = load_cast_data()
    except Exception as e:
        logger.warning(f"Cast 데이터 로드 실패 (cast 정보 없이 계속 진행): {e}")
        cast_df = None
    
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
            (current_page == "search" and search_query) or
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

    # 현재 사용자 정보 가져오기 (다른 로직보다 먼저 실행)
    current_user = get_current_user_from_cookies(request)
    logger.info(f"현재 사용자 상태: is_logged_in={current_user is not None}, current_user={current_user}")
    
    if FIREBASE_AVAILABLE:
        try:
            firebase_available = get_firebase_manager().initialized
        except:
            firebase_available = False
    else:
        firebase_available = False
    is_logged_in = current_user is not None

    # 영화 기반 추천: 영화 검색 및 선택
    if current_page == "movie_based" and df_movies is not None:
        if movie_search_query and movie_search_query.strip():
            try:
                df_search = search_movies_cached(query=movie_search_query, limit=10)
                movie_search_results = from_dataframe(df_search, cast_df=cast_df)
            except Exception as e:
                logger.error(f"영화 검색 실패: {e}", exc_info=True)
        
        # 선택된 영화 정보 가져오기
        if selected_movie_id and df_movies is not None:
            try:
                movie_row = df_movies[df_movies["movie_id"] == selected_movie_id]
                if not movie_row.empty:
                    selected_movie_info = from_dataframe(movie_row.head(1), cast_df=cast_df)[0]
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
                        "top_watched": from_dataframe(top_watched_df, include_rating=True, cast_df=cast_df),
                        "recommendations": from_dataframe(recommendations_df, include_predicted=True, cast_df=cast_df),
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
                    "items": from_dataframe(similar_df, include_similarity=True, cast_df=cast_df),
                }
            except ValueError as exc:
                errors.append(str(exc))
    
    # 자연어 검색 결과
    search_results = None
    if current_page == "search" and search_query and search_query.strip():
        try:
            from app.api.routes.search import get_search_pipeline
            search_pipeline = get_search_pipeline()
            
            # 검색 실행
            search_response = search_pipeline.search_to_response(
                query=search_query,
                top_k=limit,
                min_score=0.0
            )
            
            # 활동 로깅 추가
            try:
                from app.api.user_activity_logger import get_activity_logger
                activity_logger = get_activity_logger()
                
                # 결과 영화 ID 리스트 추출
                result_movie_ids = [r.movie_id for r in search_response.results]
                
                # 검색 로깅 (세션 ID 생성 및 응답에 포함)
                session_id = activity_logger.log_search(
                    request=request,
                    query=search_query,
                    result_count=search_response.total_results,
                    result_movie_ids=result_movie_ids,
                    search_type="natural_language"
                )
                search_response.session_id = session_id
                logger.info(f"✅ 검색 로깅 완료: session_id={session_id}")
            except Exception as log_error:
                logger.warning(f"검색 로깅 실패 (계속 진행): {log_error}")
            
            # 검색 결과를 DataFrame으로 변환하고 영화 메타데이터와 조인
            if search_response.results:
                # 검색 결과에서 movie_id와 score 추출
                search_movie_ids = []
                search_scores = {}
                for result in search_response.results:
                    search_movie_ids.append(result.movie_id)
                    search_scores[result.movie_id] = result.score
                
                # df_movies가 없으면 로드
                if df_movies is None:
                    logger.info("검색 결과 메타데이터를 위해 영화 데이터 로드 중...")
                    df_movies, _, _ = load_all_data()
                
                # movie_id로 전체 영화 데이터 조인
                df_search_movies = df_movies[df_movies["movie_id"].isin(search_movie_ids)].copy()
                
                if not df_search_movies.empty:
                    # 검색 결과 순서 유지
                    df_search_movies["movie_id_str"] = df_search_movies["movie_id"].astype(str)
                    search_movie_ids_str = [str(mid) for mid in search_movie_ids]
                    df_search_movies = df_search_movies.set_index("movie_id_str").reindex(search_movie_ids_str).reset_index(drop=True)
                    
                    # from_dataframe으로 표준 형식 변환
                    search_movies = from_dataframe(df_search_movies, cast_df=cast_df)
                    
                    # 검색 점수 추가
                    for movie in search_movies:
                        movie["score"] = search_scores.get(movie["movie_id"], 0.0)
                    
                    search_results = {
                        "query": search_query,
                        "total_results": len(search_movies),
                        "results": search_movies
                    }
                    logger.info(f"🔍 자연어 검색 완료: '{search_query}' -> {len(search_movies)}개 결과 (메타데이터 포함)")
                else:
                    search_results = {
                        "query": search_query,
                        "total_results": 0,
                        "results": []
                    }
            else:
                search_results = {
                    "query": search_query,
                    "total_results": 0,
                    "results": []
                }
        except Exception as exc:
            logger.error(f"❌ 자연어 검색 실패: {exc}", exc_info=True)
            errors.append(f"검색 중 오류가 발생했습니다: {str(exc)}")
    
    # 포스터 검색 결과
    poster_search_results = None
    if current_page == "poster_search" and poster_query and poster_query.strip():
        try:
            from app.api.routes.poster_search import poster_search_by_text
            
            # 포스터 검색 실행 (이미 모든 메타데이터 포함)
            poster_response = poster_search_by_text(
                request=request,
                query=poster_query,
                limit=limit,
                include_cast=True
            )
            
            # 검색 결과를 표준 형식으로 변환
            if poster_response.results:
                # PosterSearchResultMovie를 딕셔너리로 변환 (이미 모든 메타데이터 포함)
                poster_movies = []
                for result in poster_response.results:
                    movie_dict = {
                        "movie_id": result.movie_id,
                        "title": result.title,
                        "total_title": result.title,  # 호환성을 위해
                        "genres": result.genres,
                        "genres_tmdb": result.genres,  # 호환성을 위해
                        "year": result.year,
                        "overview": result.overview,
                        "poster_url": result.poster_url,
                        "similarity": result.score,  # 유사도로 표시
                        "cast_info": result.cast_info,
                        # 추가 메타데이터
                        "imdb_id": result.imdb_id,
                        "release_date": result.release_date,
                        "vote_average": result.vote_average,
                        "vote_count": result.vote_count,
                        "adult": result.adult,
                        "language": result.language,
                    }
                    poster_movies.append(movie_dict)
                
                poster_search_results = {
                    "query": poster_query,
                    "query_type": "text",
                    "total_results": len(poster_movies),
                    "results": poster_movies,
                    "session_id": poster_response.session_id
                }
                logger.info(f"🖼️ 포스터 검색 완료: '{poster_query}' -> {len(poster_movies)}개 결과")
            else:
                poster_search_results = {
                    "query": poster_query,
                    "query_type": "text",
                    "total_results": 0,
                    "results": []
                }
        except Exception as exc:
            logger.error(f"❌ 포스터 검색 실패: {exc}", exc_info=True)
            errors.append(f"포스터 검색 중 오류가 발생했습니다: {str(exc)}")
    
                # 평점 관리 페이지 데이터 로드
    rating_search_results = []
    selected_rating_movie_info = None
    explored_movies_list = []
    user_ratings_list = []
    rating_stats = {
        "total": 0,
        "avg": 0.0,
        "high": 0,
        "low": 0,
    }
    if current_page == "rating_management" and is_logged_in and firebase_available:                                                                             
        try:
            # 영화 검색 결과 (평점 입력용) - 평점 관리에서는 더 많은 결과 표시
            if query:
                # 평점 관리에서는 최대 200개까지 검색 결과 표시 (모든 결과를 보여주기 위해)                                                                    
                rating_limit = 200  # 더 많은 결과 표시
                df_search = search_movies_cached(query=query, limit=rating_limit)                                                                               
                rating_search_results = from_dataframe(df_search, cast_df=cast_df)
            
            # 선택된 영화 정보 가져오기
            if selected_rating_movie_id and df_movies is not None:
                try:
                    movie_row = df_movies[df_movies["movie_id"] == selected_rating_movie_id]                                                                                                                                                    
                    if not movie_row.empty:
                        selected_rating_movie_info = from_dataframe(movie_row.head(1), cast_df=cast_df)[0]                                                                       
                except Exception as e:
                    logger.error(f"평점 관리 영화 정보 조회 실패: {e}", exc_info=True)
            
            # 탐색된 영화 결과 가져오기
            if explored_movie_ids and df_movies is not None:
                try:
                    movie_id_list = [mid.strip() for mid in explored_movie_ids.split(",") if mid.strip()]
                    if movie_id_list:
                        # movie_id 타입 변환 (데이터프레임과 동일한 타입으로)
                        df_movies_id_type = df_movies["movie_id"].dtype
                        if pd.api.types.is_integer_dtype(df_movies_id_type):
                            movie_id_list = [int(mid) if mid.isdigit() else mid for mid in movie_id_list]
                        else:
                            movie_id_list = [str(mid) for mid in movie_id_list]
                        
                        explored_df = df_movies[df_movies["movie_id"].isin(movie_id_list)].copy()
                        if not explored_df.empty:
                            # 원래 순서 유지하기 위해 movie_id를 문자열로 변환하여 정렬
                            explored_df["movie_id_str"] = explored_df["movie_id"].astype(str)
                            movie_id_list_str = [str(mid) for mid in movie_id_list]
                            explored_df = explored_df.set_index("movie_id_str").reindex(movie_id_list_str).reset_index(drop=True)
                            explored_movies_list = from_dataframe(explored_df, cast_df=cast_df)
                except Exception as e:
                    logger.error(f"탐색 영화 정보 조회 실패: {e}", exc_info=True)
            
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
        "search_query": search_query or "",
        "search_results": search_results,
        "poster_query": poster_query or "",
        "poster_search_results": poster_search_results,
        "query": query or "",
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
        "selected_rating_movie_id": selected_rating_movie_id or "",
        "selected_rating_movie_info": selected_rating_movie_info,
        "explored_movies_list": explored_movies_list,
        "explored_movie_ids": explored_movie_ids or "",
        "user_ratings_list": user_ratings_list,
        "rating_stats": rating_stats,
        "explore_count": explore_count,
    }

    total_time = time.time() - request_start
    logger.info(f"✅ 전체 요청 처리 완료: {total_time:.3f}초 (페이지: {current_page})")
    
    return templates.TemplateResponse("index.html", context)

