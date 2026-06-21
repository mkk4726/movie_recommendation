"""
Home page route for rendering the HTML frontend.
"""

import logging
import time
from pathlib import Path
from typing import Annotated, List, Optional

import pandas as pd
import yaml
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.app_state import get_loading_state
from app.api.utils import _safe_year, from_dataframe, get_current_user_from_cookies, log_search_activity
from app.services.data_access import (
    get_data_stats,
    get_sample_user_ids,
    load_cast_data,
    load_movie_data,
    search_movies_cached,
    user_exists,
)
from app.services.recommender_service import get_item_cf_pipeline, get_user_cf_pipeline
from core.user_system.db_manager import get_user_manager

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# 쿼리 파라미터 묶음
# ---------------------------------------------------------------------------


class HomeQueryParams:
    """home() 라우트의 28개 쿼리 파라미터를 하나의 객체로 묶습니다."""

    def __init__(
        self,
        page: Optional[str] = Query("search", description="페이지 타입"),
        query: Optional[str] = Query(None),
        limit: int = Query(10, ge=1, le=200),
        user_id: Optional[str] = Query(None),
        user_top_n: int = Query(10, ge=5, le=20),
        user_option: Optional[str] = Query(None, description="사용자 선택 옵션: me 또는 other"),
        movie_search_query: Optional[str] = Query(None, description="영화 검색 쿼리"),
        selected_movie_id: Optional[str] = Query(None, description="선택된 영화 ID"),
        similar_top_n: int = Query(10, ge=5, le=15),
        movie_genre: Optional[List[str]] = Query(None, description="장르 필터 (영화 기반 추천)"),
        movie_language: Optional[List[str]] = Query(None, description="언어 필터 (영화 기반 추천)"),
        search_query: Optional[str] = Query(None, description="자연어 검색 쿼리"),
        poster_query: Optional[str] = Query(None, description="포스터 검색 쿼리"),
        min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점"),
        min_vote_count: int = Query(0, ge=0, description="최소 평가 수"),
        search_genre: Optional[List[str]] = Query(None, description="장르 필터 (자연어 검색)"),
        search_language: Optional[List[str]] = Query(None, description="언어 필터 (자연어 검색)"),
        poster_genre: Optional[List[str]] = Query(None, description="장르 필터 (포스터 검색)"),
        poster_language: Optional[List[str]] = Query(None, description="언어 필터 (포스터 검색)"),
        rating_method: Optional[str] = Query("search", description="평점 입력 방식"),
        rating_movie_id: Optional[str] = Query(None, description="평점 입력할 영화 ID"),
        rating_value: Optional[float] = Query(None, ge=0.5, le=5.0, description="평점 값"),
        selected_rating_movie_id: Optional[str] = Query(None, description="평점 관리에서 선택된 영화 ID"),
        explore_count: int = Query(10, ge=5, le=20, description="탐색할 영화 개수"),
        explored_movie_ids: Optional[str] = Query(None, description="탐색된 영화 ID들 (쉼표로 구분)"),
        auth_error: Optional[str] = Query(None, description="인증 에러 메시지"),
    ):
        self.page = page
        self.query = query
        self.limit = limit
        self.user_id = user_id
        self.user_top_n = user_top_n
        self.user_option = user_option
        self.movie_search_query = movie_search_query
        self.selected_movie_id = selected_movie_id
        self.similar_top_n = similar_top_n
        self.movie_genre = movie_genre
        self.movie_language = movie_language
        self.search_query = search_query
        self.poster_query = poster_query
        self.min_rating = min_rating
        self.min_vote_count = min_vote_count
        self.search_genre = search_genre
        self.search_language = search_language
        self.poster_genre = poster_genre
        self.poster_language = poster_language
        self.rating_method = rating_method
        self.rating_movie_id = rating_movie_id
        self.rating_value = rating_value
        self.selected_rating_movie_id = selected_rating_movie_id
        self.explore_count = explore_count
        self.explored_movie_ids = explored_movie_ids
        self.auth_error = auth_error


# ---------------------------------------------------------------------------
# 페이지별 처리 함수
# ---------------------------------------------------------------------------


def _handle_movie_based(
    movie_search_query,
    selected_movie_id,
    df_movies,
    cast_df,
    item_cf,
    similar_top_n,
    movie_genre,
    movie_language,
    errors,
):
    """영화 기반 추천 페이지 데이터를 처리합니다."""
    movie_search_results = []
    selected_movie_info = None
    similar_movies = None

    if movie_search_query and movie_search_query.strip():
        try:
            df_search = search_movies_cached(query=movie_search_query, limit=10)
            movie_search_results = from_dataframe(df_search, cast_df=cast_df)
        except Exception as e:
            logger.error(f"영화 검색 실패: {e}", exc_info=True)

    if selected_movie_id:
        if df_movies is not None:
            try:
                movie_row = df_movies[df_movies["movie_id"] == selected_movie_id]
                if not movie_row.empty:
                    selected_movie_info = from_dataframe(movie_row.head(1), cast_df=cast_df)[0]
            except Exception as e:
                logger.error(f"영화 정보 조회 실패: {e}", exc_info=True)

        try:
            filters = {}
            if movie_genre:
                filters["genre"] = movie_genre
            if movie_language:
                filters["language"] = movie_language
            similar_df = item_cf.search(
                movie_id=selected_movie_id,
                top_n=similar_top_n,
                filters=filters or None,
            )
            if not similar_df.empty:
                similar_movies = {
                    "movie_id": selected_movie_id,
                    "items": from_dataframe(similar_df, include_similarity=True, cast_df=cast_df),
                }
            else:
                errors.append(f"영화 ID '{selected_movie_id}'를 영화 데이터에서 찾을 수 없습니다.")
        except (ValueError, FileNotFoundError) as exc:
            errors.append(str(exc))

    return movie_search_results, selected_movie_info, similar_movies


def _handle_user_based(user_id, user_option, is_logged_in, current_user, user_cf, cast_df, user_top_n, errors):
    """사용자 기반 추천 페이지 데이터를 처리합니다."""
    if user_option == "me" and is_logged_in and current_user:
        user_id = current_user.get("user_id")

    if not user_id:
        return None, user_id

    if not user_exists(user_id):
        msg = (
            "아직 학습되기 전입니다. 더 많은 평점을 입력해주세요."
            if user_option == "me"
            else f"사용자 '{user_id}'를 평점 데이터에서 찾을 수 없습니다."
        )
        errors.append(msg)
        return None, user_id

    try:
        top_watched_df, recommendations_df = user_cf.recommend(user_id=user_id, top_n=user_top_n)
        return {
            "user_id": user_id,
            "top_watched": from_dataframe(top_watched_df, include_rating=True, cast_df=cast_df),
            "recommendations": from_dataframe(recommendations_df, include_predicted=True, cast_df=cast_df),
        }, user_id
    except (ValueError, FileNotFoundError) as exc:
        errors.append(str(exc))
        return None, user_id


def _handle_search(
    request,
    search_query,
    limit,
    min_rating,
    min_vote_count,
    search_genre,
    search_language,
    df_movies,
    cast_df,
    errors,
):
    """자연어 검색 페이지 데이터를 처리합니다."""
    from app.api.routes.search import get_search_pipeline

    try:
        search_response = get_search_pipeline().search(
            query=search_query,
            top_n=limit,
            min_rating=min_rating,
            min_vote_count=min_vote_count,
            genre_filter=search_genre,
            language_filter=search_language,
            include_cast=True,
        )

        result_movie_ids = [r.movie_id for r in search_response.results]
        session_id = log_search_activity(
            request,
            query=search_query,
            result_count=search_response.total_results,
            result_movie_ids=result_movie_ids,
            search_type="natural_language",
        )
        search_response.session_id = session_id

        if not search_response.results:
            return {"query": search_query, "total_results": 0, "results": []}

        search_scores = {r.movie_id: r.score for r in search_response.results}
        search_movie_ids = [r.movie_id for r in search_response.results]

        if df_movies is None:
            df_movies = load_movie_data()

        df_search = df_movies[df_movies["movie_id"].isin(search_movie_ids)].copy()
        if df_search.empty:
            return {"query": search_query, "total_results": 0, "results": []}

        df_search["movie_id_str"] = df_search["movie_id"].astype(str)
        df_search = (
            df_search.set_index("movie_id_str").reindex([str(mid) for mid in search_movie_ids]).reset_index(drop=True)
        )
        df_search = df_search.dropna(subset=["movie_id"])
        movies_list = from_dataframe(df_search, cast_df=cast_df)
        for movie in movies_list:
            movie["score"] = search_scores.get(movie["movie_id"], 0.0)

        logger.info(f"자연어 검색 완료: '{search_query}' -> {len(movies_list)}개 결과")
        return {
            "query": search_query,
            "total_results": len(movies_list),
            "results": movies_list,
            "session_id": session_id,
        }
    except Exception as exc:
        logger.error(f"자연어 검색 실패: {exc}", exc_info=True)
        errors.append(f"검색 중 오류가 발생했습니다: {str(exc)}")
        return None


def _handle_poster_search(
    request,
    poster_query,
    limit,
    min_rating,
    min_vote_count,
    poster_genre,
    poster_language,
    errors,
):
    """포스터 검색 페이지 데이터를 처리합니다."""
    from app.services.clip_service import get_poster_search_pipeline

    try:
        filters = {}
        if min_rating > 0:
            filters["min_rating"] = min_rating
        if min_vote_count > 0:
            filters["min_vote_count"] = min_vote_count
        if poster_genre:
            filters["genre"] = poster_genre
        if poster_language:
            filters["language"] = poster_language

        raw = get_poster_search_pipeline().search(
            query=poster_query,
            top_n=limit,
            filters=filters or None,
            include_cast=True,
        )

        if not raw:
            return {"query": poster_query, "query_type": "text", "total_results": 0, "results": []}

        poster_movies = [
            {
                **item,
                "total_title": item.get("title"),
                "genres_tmdb": item.get("genres"),
                "similarity": item.get("score"),
            }
            for item in raw
        ]
        result_ids = [m["movie_id"] for m in poster_movies]
        session_id = log_search_activity(
            request,
            query=poster_query,
            result_count=len(poster_movies),
            result_movie_ids=result_ids,
            search_type="poster",
            filters=filters,
        )
        logger.info(f"포스터 검색 완료: '{poster_query}' -> {len(poster_movies)}개 결과")
        return {
            "query": poster_query,
            "query_type": "text",
            "total_results": len(poster_movies),
            "results": poster_movies,
            "session_id": session_id,
        }
    except Exception as exc:
        logger.error(f"포스터 검색 실패: {exc}", exc_info=True)
        errors.append(f"포스터 검색 중 오류가 발생했습니다: {str(exc)}")
        return None


def _handle_rating_management(
    query, selected_rating_movie_id, explored_movie_ids, current_user, df_movies, cast_df, errors
):
    """평점 관리 페이지 데이터를 처리합니다."""
    rating_search_results = []
    selected_rating_movie_info = None
    explored_movies_list = []
    user_ratings_list = []
    rating_stats = {"total": 0, "avg": 0.0, "high": 0, "low": 0}

    try:
        if query:
            df_search = search_movies_cached(query=query, limit=200)
            rating_search_results = from_dataframe(df_search, cast_df=cast_df)

        if selected_rating_movie_id and df_movies is not None:
            try:
                movie_row = df_movies[df_movies["movie_id"] == selected_rating_movie_id]
                if not movie_row.empty:
                    selected_rating_movie_info = from_dataframe(movie_row.head(1), cast_df=cast_df)[0]
            except Exception as e:
                logger.error(f"평점 관리 영화 정보 조회 실패: {e}", exc_info=True)

        if explored_movie_ids and df_movies is not None:
            try:
                movie_id_list = [mid.strip() for mid in explored_movie_ids.split(",") if mid.strip()]
                if movie_id_list:
                    df_movies_id_type = df_movies["movie_id"].dtype
                    if pd.api.types.is_integer_dtype(df_movies_id_type):
                        movie_id_list = [int(mid) if mid.isdigit() else mid for mid in movie_id_list]
                    else:
                        movie_id_list = [str(mid) for mid in movie_id_list]

                    explored_df = df_movies[df_movies["movie_id"].isin(movie_id_list)].copy()
                    if not explored_df.empty:
                        explored_df["movie_id_str"] = explored_df["movie_id"].astype(str)
                        movie_id_list_str = [str(mid) for mid in movie_id_list]
                        explored_df = (
                            explored_df.set_index("movie_id_str").reindex(movie_id_list_str).reset_index(drop=True)
                        )
                        explored_movies_list = from_dataframe(explored_df, cast_df=cast_df)
            except Exception as e:
                logger.error(f"탐색 영화 정보 조회 실패: {e}", exc_info=True)

        user_uid = current_user.get("user_id")
        if user_uid:
            raw_ratings = get_user_manager().get_user_ratings(user_uid)
            for rating_row in raw_ratings:
                movie_id = str(rating_row.get("movie_id", ""))
                rating = rating_row.get("rating", 0)
                movie_row = df_movies[df_movies["movie_id"] == movie_id] if df_movies is not None else pd.DataFrame()
                if not movie_row.empty:
                    movie_data = movie_row.iloc[0]
                    user_ratings_list.append(
                        {
                            "movie_id": movie_id,
                            "title": movie_data.get("title") or movie_data.get("movie_title", "N/A"),
                            "year": _safe_year(movie_data.get("year")),
                            "genre": movie_data.get("genre"),
                            "rating": rating,
                            "created_at": "",
                        }
                    )

            ratings_list = [r["rating"] for r in raw_ratings]
            rating_stats = {
                "total": len(ratings_list),
                "avg": sum(ratings_list) / len(ratings_list) if ratings_list else 0,
                "high": len([r for r in ratings_list if r >= 4.0]),
                "low": len([r for r in ratings_list if r <= 2.0]),
            }
    except Exception as e:
        errors.append(f"평점 데이터 로드 실패: {str(e)}")

    return rating_search_results, selected_rating_movie_info, explored_movies_list, user_ratings_list, rating_stats


# ---------------------------------------------------------------------------
# 라우트
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def home(request: Request, p: Annotated[HomeQueryParams, Depends()]):
    """Render a simple HTML frontend for interacting with the recommender."""
    loading_state = get_loading_state()
    if loading_state["is_loading"]:
        return templates.TemplateResponse(
            "loading.html",
            {
                "request": request,
                "loading_message": loading_state["loading_message"],
                "progress": loading_state["progress"],
            },
        )

    request_start = time.time()
    errors: List[str] = []
    if p.auth_error:
        errors.append(p.auth_error)

    current_page = p.page or "movie_based"
    current_user = get_current_user_from_cookies(request)
    is_logged_in = current_user is not None
    logger.info(f"현재 사용자 상태: is_logged_in={is_logged_in}, current_user={current_user}")

    user_cf = get_user_cf_pipeline()
    item_cf = get_item_cf_pipeline()

    try:
        cast_df = load_cast_data()
    except Exception as e:
        logger.warning(f"Cast 데이터 로드 실패 (cast 정보 없이 계속 진행): {e}")
        cast_df = None

    stats_start = time.time()
    try:
        stats = get_data_stats()
        logger.debug(f"통계 정보 로드: {time.time() - stats_start:.3f}초")
    except Exception as exc:
        logger.error(f"통계 정보 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)
        stats = {"total_movies": "0", "total_ratings": "0", "total_users": "0", "avg_rating": None}

    df_movies = None
    needs_full_data = (
        (current_page == "movie_based" and (p.selected_movie_id or p.movie_search_query))
        or (current_page == "search" and p.search_query)
        or current_page == "rating_management"
    )
    if needs_full_data:
        try:
            df_movies = load_movie_data()
        except Exception as exc:
            logger.error(f"데이터 로드 실패: {type(exc).__name__}: {exc}", exc_info=True)

    # 페이지별 처리
    movie_search_results, selected_movie_info, similar_movies = [], None, None
    user_recommendations = None
    search_results = None
    poster_search_results = None
    rating_search_results, selected_rating_movie_info, explored_movies_list, user_ratings_list, rating_stats = (
        [],
        None,
        [],
        [],
        {"total": 0, "avg": 0.0, "high": 0, "low": 0},
    )
    user_id = p.user_id

    if current_page == "movie_based":
        movie_search_results, selected_movie_info, similar_movies = _handle_movie_based(
            p.movie_search_query,
            p.selected_movie_id,
            df_movies,
            cast_df,
            item_cf,
            p.similar_top_n,
            p.movie_genre,
            p.movie_language,
            errors,
        )

    elif current_page == "user_based":
        user_recommendations, user_id = _handle_user_based(
            p.user_id,
            p.user_option,
            is_logged_in,
            current_user,
            user_cf,
            cast_df,
            p.user_top_n,
            errors,
        )

    elif current_page == "search" and p.search_query and p.search_query.strip():
        search_results = _handle_search(
            request,
            p.search_query,
            p.limit,
            p.min_rating,
            p.min_vote_count,
            p.search_genre,
            p.search_language,
            df_movies,
            cast_df,
            errors,
        )

    elif current_page == "poster_search" and p.poster_query and p.poster_query.strip():
        poster_search_results = _handle_poster_search(
            request,
            p.poster_query,
            p.limit,
            p.min_rating,
            p.min_vote_count,
            p.poster_genre,
            p.poster_language,
            errors,
        )

    elif current_page == "rating_management" and is_logged_in:
        rating_search_results, selected_rating_movie_info, explored_movies_list, user_ratings_list, rating_stats = (
            _handle_rating_management(
                p.query,
                p.selected_rating_movie_id,
                p.explored_movie_ids,
                current_user,
                df_movies,
                cast_df,
                errors,
            )
        )

    config_path = BASE_DIR.parent / "config" / "app.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config_options = yaml.safe_load(f)

    available_users = []
    if current_page == "user_based":
        try:
            available_users = get_sample_user_ids(100)
        except Exception:
            pass

    context = {
        "request": request,
        "title": "볼거 없나? 추천 서비스",
        "current_page": current_page,
        "search_query": p.search_query or "",
        "search_results": search_results,
        "poster_query": p.poster_query or "",
        "poster_search_results": poster_search_results,
        "query": p.query or "",
        "search_limit": p.limit,
        "min_rating": p.min_rating,
        "min_vote_count": p.min_vote_count,
        "search_genre": p.search_genre or [],
        "search_language": p.search_language or [],
        "poster_genre": p.poster_genre or [],
        "poster_language": p.poster_language or [],
        "movie_search_query": p.movie_search_query or "",
        "movie_search_results": movie_search_results,
        "selected_movie_id": p.selected_movie_id or "",
        "selected_movie_info": selected_movie_info,
        "rating_search_results": rating_search_results,
        "user_id": user_id or "",
        "user_option": p.user_option or "",
        "user_top_n": p.user_top_n,
        "user_recommendations": user_recommendations,
        "available_users": available_users,
        "similar_top_n": p.similar_top_n,
        "similar_movies": similar_movies,
        "movie_genre": p.movie_genre or [],
        "movie_language": p.movie_language or [],
        "config_options": config_options,
        "errors": errors,
        "stats": stats,
        "model_loaded": True,
        "is_logged_in": is_logged_in,
        "current_user": current_user,
        "rating_method": p.rating_method or "search",
        "rating_movie_id": p.rating_movie_id or "",
        "selected_rating_movie_id": p.selected_rating_movie_id or "",
        "selected_rating_movie_info": selected_rating_movie_info,
        "explored_movies_list": explored_movies_list,
        "explored_movie_ids": p.explored_movie_ids or "",
        "user_ratings_list": user_ratings_list,
        "rating_stats": rating_stats,
        "explore_count": p.explore_count,
    }

    logger.info(f"전체 요청 처리 완료: {time.time() - request_start:.3f}초 (페이지: {current_page})")
    return templates.TemplateResponse("index.html", context)
