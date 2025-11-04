"""
Rating management API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import RedirectResponse

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import get_firebase_manager
    from user_system.firebase_firestore import FirestoreManager
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from app.api.utils import get_current_user_from_cookies

# 탐색 기능을 위한 import
try:
    from cold_start.show_random_movies import get_random_popular_movies
    from modules.services.data_access import load_all_data
    EXPLORE_AVAILABLE = True
except ImportError:
    EXPLORE_AVAILABLE = False

router = APIRouter()


@router.post("/rating/add")
async def add_rating(
    request: Request,
    movie_id: str = Form(...),
    rating: float = Form(..., ge=0.5, le=5.0),
    page: Optional[str] = Form("rating_management"),
    rating_method: Optional[str] = Form("search"),
    query: Optional[str] = Form(None),
    selected_rating_movie_id: Optional[str] = Form(None),
    explore_count: Optional[int] = Form(None),
    explored_movie_ids: Optional[str] = Form(None),
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
            # 리다이렉트 URL 구성
            redirect_params = [f"page={page}", f"rating_method={rating_method}"]
            if query:
                redirect_params.append(f"query={query}")
            if selected_rating_movie_id:
                redirect_params.append(f"selected_rating_movie_id={selected_rating_movie_id}")
            if explore_count is not None:
                redirect_params.append(f"explore_count={explore_count}")
            if explored_movie_ids:
                redirect_params.append(f"explored_movie_ids={explored_movie_ids}")
            redirect_url = f"/?{'&'.join(redirect_params)}"
            return RedirectResponse(url=redirect_url, status_code=303)
        else:
            raise HTTPException(status_code=500, detail="평점 저장에 실패했습니다.")                                                                           
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평점 저장 실패: {str(e)}")


@router.post("/rating/delete")
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


@router.post("/rating/explore")
async def explore_movies(
    request: Request,
    explore_count: int = Form(10, ge=5, le=20),
    page: Optional[str] = Form("rating_management"),
    rating_method: Optional[str] = Form("explore"),
):
    """랜덤 영화 탐색"""
    if not EXPLORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="탐색 기능이 사용 불가능합니다.")
    
    try:
        # 데이터 로드
        df_movies, df_ratings, _ = load_all_data()
        
        # 랜덤 영화 선택 (이미 본 영화는 제외하지 않음 - 간단한 구현)
        random_movies, _ = get_random_popular_movies(
            df_ratings=df_ratings,
            df_movies=df_movies,
            n_movies=explore_count,
            exclude_movie_ids=None
        )
        
        # 선택된 영화 ID들을 쿼리 파라미터로 전달
        if not random_movies.empty:
            explored_movie_ids = ",".join(random_movies["movie_id"].astype(str).tolist())
            redirect_url = f"/?page={page}&rating_method={rating_method}&explore_count={explore_count}&explored_movie_ids={explored_movie_ids}"
        else:
            redirect_url = f"/?page={page}&rating_method={rating_method}&explore_count={explore_count}"
        
        return RedirectResponse(url=redirect_url, status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"탐색 실패: {str(e)}")

