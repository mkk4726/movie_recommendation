"""
FastAPI application exposing the movie recommender functionality as HTTP endpoints.
Includes a simple server-rendered frontend built with Jinja2 templates.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from modules.core import add_project_paths
from modules.services.data_access import load_all_data, search_movies_cached
from modules.services.recommender_service import get_recommender_service

add_project_paths()

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import setup_firebase_config, get_firebase_manager, FirestoreCollections
    from user_system.firebase_auth import FirebaseAuthManager
    from user_system.firebase_firestore import FirestoreManager
    from datetime import datetime
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class MovieSummary(BaseModel):
    movie_id: str
    title: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None


class UserRatedMovie(MovieSummary):
    rating: Optional[float] = None


class RecommendedMovie(MovieSummary):
    predicted_rating: Optional[float] = None


class SimilarMovie(MovieSummary):
    similarity: Optional[float] = None


class UserRecommendationResponse(BaseModel):
    user_id: str
    top_watched: List[UserRatedMovie]
    recommendations: List[RecommendedMovie]


class SimilarMoviesResponse(BaseModel):
    movie_id: str
    similar: List[SimilarMovie]


class SearchResponse(BaseModel):
    query: str
    results: List[MovieSummary]


app = FastAPI(
    title="Movie Recommendation Backend",
    description="FastAPI service that wraps the existing recommendation models.",
    version="0.1.0",
)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Firebase 초기화 (앱 시작 시)
if FIREBASE_AVAILABLE:
    try:
        setup_firebase_config()
    except Exception as e:
        print(f"Firebase 초기화 실패: {e}")


def get_current_user_from_cookies(request: Request) -> Optional[Dict[str, Any]]:
    """쿠키에서 현재 사용자 정보 가져오기"""
    if not FIREBASE_AVAILABLE:
        return None
    
    try:
        auth_token = request.cookies.get("auth_token")
        user_uid = request.cookies.get("user_uid")
        
        if auth_token and user_uid and auth_token.startswith("demo_token_"):
            firebase_manager = get_firebase_manager()
            if not firebase_manager.initialized:
                return None
            
            db = firebase_manager.get_firestore()
            user_doc = db.collection("users").document(user_uid).get()
            
            if user_doc.exists:
                return user_doc.to_dict()
            else:
                # 기본 사용자 정보
                return {
                    "uid": user_uid,
                    "email": "user@example.com",
                    "display_name": "User"
                }
    except Exception:
        pass
    
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


def _from_dataframe(
    df: pd.DataFrame,
    *,
    include_rating: bool = False,
    include_predicted: bool = False,
    include_similarity: bool = False,
) -> List[dict]:
    if df is None or df.empty:
        return []

    records = []
    for row in df.to_dict(orient="records"):
        title = row.get("title") or row.get("movie_title")
        record = {
            "movie_id": str(row.get("movie_id", "")),
            "title": title,
            "genre": row.get("genre"),
            "year": _safe_year(row.get("year")),
        }
        if include_rating:
            record["rating"] = _safe_number(row.get("rating"))
        if include_predicted:
            record["predicted_rating"] = _safe_number(row.get("predicted_rating"))
        if include_similarity:
            record["similarity"] = _safe_number(row.get("similarity"))
        records.append(record)
    return records


@app.get("/", response_class=HTMLResponse)
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

    # Load recommender only if needed
    recommender_service = None
    if user_id or movie_id:
        try:
            recommender_service = get_recommender_service()
        except FileNotFoundError as exc:
            errors.append(str(exc))

    df_movies = None
    df_ratings = None
    stats = {
        "total_movies": "0",
        "total_ratings": "0",
        "total_users": "0",
        "avg_rating": None,
    }
    model_loaded = False
    
    # 데이터 로드 시도 (사이드바 통계용)
    try:
        df_movies, df_ratings, _ = load_all_data()
        if df_movies is not None and df_ratings is not None:
            stats = {
                "total_movies": f"{len(df_movies):,}",
                "total_ratings": f"{len(df_ratings):,}",
                "total_users": f"{df_ratings['user_id'].nunique():,}" if "user_id" in df_ratings.columns else "0",
                "avg_rating": float(df_ratings["rating"].mean()) if "rating" in df_ratings.columns else None,
            }
    except (FileNotFoundError, Exception):
        pass  # 데이터 로드 실패해도 계속 진행
    
    if recommender_service is not None:
        model_loaded = True

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
                    "top_watched": _from_dataframe(top_watched_df, include_rating=True),
                    "recommendations": _from_dataframe(recommendations_df, include_predicted=True),
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
                    "items": _from_dataframe(similar_df, include_similarity=True),
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
                rating_search_results = _from_dataframe(df_search)
            
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


@app.get("/health")
def healthcheck() -> dict:
    """Liveness probe."""
    try:
        # Touch the recommender lazily to surface model path errors early.
        get_recommender_service()
        return {"status": "ok"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/movies/search", response_model=SearchResponse)
def search_movies(query: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    try:
        df = search_movies_cached(query=query, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    results = _from_dataframe(df)
    return SearchResponse(query=query, results=results)


@app.get("/users/{user_id}/recommendations", response_model=UserRecommendationResponse)
def recommend_for_user(
    user_id: str,
    top_n: int = Query(10, ge=1, le=50),
):
    recommender = get_recommender_service()
    try:
        df_movies, df_ratings, _ = load_all_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if user_id not in df_ratings["user_id"].values:
        raise HTTPException(
            status_code=404,
            detail=f"User '{user_id}' not found in ratings dataset.",
        )

    try:
        top_watched_df, recommendations_df = recommender.recommend_for_user(
            user_id=user_id,
            df_movies=df_movies,
            n=top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    top_watched = _from_dataframe(top_watched_df, include_rating=True)
    recommendations = _from_dataframe(recommendations_df, include_predicted=True)

    return UserRecommendationResponse(
        user_id=user_id,
        top_watched=top_watched,
        recommendations=recommendations,
    )


@app.get("/movies/{movie_id}/similar", response_model=SimilarMoviesResponse)
def similar_movies(
    movie_id: str,
    top_n: int = Query(10, ge=1, le=50),
    genre: Optional[List[str]] = Query(None),
    min_year: Optional[int] = Query(None, ge=1800),
    max_year: Optional[int] = Query(None, ge=1800),
):
    recommender = get_recommender_service()
    try:
        df_movies, _, _ = load_all_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if movie_id not in df_movies["movie_id"].values:
        raise HTTPException(
            status_code=404,
            detail=f"Movie '{movie_id}' not found in movie catalog.",
        )

    filters = {}
    if genre:
        filters["genre"] = genre
    if min_year is not None:
        filters["min_year"] = min_year
    if max_year is not None:
        filters["max_year"] = max_year

    try:
        similar_df = recommender.similar_movies(
            movie_id=movie_id,
            df_movies=df_movies,
            n_recommendations=top_n,
            filters=filters if filters else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Add similarity column name consistency (already handled in wrapper)
    similar = _from_dataframe(similar_df, include_similarity=True)
    return SimilarMoviesResponse(movie_id=movie_id, similar=similar)


# Firebase 인증 관련 엔드포인트
@app.post("/auth/signup")
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


@app.post("/auth/login")
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


@app.post("/auth/logout")
async def logout():
    """로그아웃"""
    response = RedirectResponse(url="/?page=movie_based", status_code=303)
    response.delete_cookie("auth_token")
    response.delete_cookie("user_uid")
    return response


# 평점 관리 관련 엔드포인트
@app.post("/rating/add")
async def add_rating(
    request: Request,
    movie_id: str = Form(...),
    rating: float = Form(..., ge=0.5, le=5.0),
    page: Optional[str] = Form("rating_management"),
    rating_method: Optional[str] = Form("search"),
):
    """평점 추가/업데이트"""
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Firebase가 사용 불가능합니다.")
    
    current_user = get_current_user_from_cookies(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    try:
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            raise HTTPException(status_code=503, detail="Firebase가 초기화되지 않았습니다.")
        
        firestore_manager = FirestoreManager()
        user_uid = current_user.get("uid")
        
        if not user_uid:
            raise HTTPException(status_code=401, detail="사용자 정보가 올바르지 않습니다.")
        
        success = firestore_manager.add_user_rating(user_uid, movie_id, rating)
        
        if success:
            redirect_url = f"/?page={page}&rating_method={rating_method}"
            return RedirectResponse(url=redirect_url, status_code=303)
        else:
            raise HTTPException(status_code=500, detail="평점 저장에 실패했습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평점 저장 실패: {str(e)}")


@app.post("/rating/delete")
async def delete_rating(
    request: Request,
    movie_id: str = Form(...),
    page: Optional[str] = Form("rating_management"),
):
    """평점 삭제"""
    if not FIREBASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Firebase가 사용 불가능합니다.")
    
    current_user = get_current_user_from_cookies(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    try:
        firebase_manager = get_firebase_manager()
        if not firebase_manager.initialized:
            raise HTTPException(status_code=503, detail="Firebase가 초기화되지 않았습니다.")
        
        firestore_manager = FirestoreManager()
        user_uid = current_user.get("uid")
        
        if not user_uid:
            raise HTTPException(status_code=401, detail="사용자 정보가 올바르지 않습니다.")
        
        success = firestore_manager.delete_user_rating(user_uid, movie_id)
        
        if success:
            redirect_url = f"/?page={page}"
            return RedirectResponse(url=redirect_url, status_code=303)
        else:
            raise HTTPException(status_code=500, detail="평점 삭제에 실패했습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평점 삭제 실패: {str(e)}")


@app.post("/rating/explore")
async def explore_movies(
    request: Request,
    explore_count: int = Form(10, ge=5, le=20),
    page: Optional[str] = Form("rating_management"),
    rating_method: Optional[str] = Form("explore"),
):
    """랜덤 영화 탐색"""
    # 탐색 기능은 아직 구현되지 않음 (추후 구현)
    redirect_url = f"/?page={page}&rating_method={rating_method}&explore_count={explore_count}"
    return RedirectResponse(url=redirect_url, status_code=303)

