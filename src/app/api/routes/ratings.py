"""
Rating management API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.services.data_access import load_movie_data, get_popular_movie_ids

from app.api.utils import get_current_user_from_cookies
from core.cold_start.show_random_movies import get_random_popular_movies
from core.user_system.db_manager import get_user_manager

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
    current_user = get_current_user_from_cookies(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자 정보가 올바르지 않습니다.")

    try:
        title = current_user.get("_movie_title")  # 전달받은 경우에만
        success = get_user_manager().add_user_rating(user_id, movie_id, title, rating)

        if success:
            redirect_params = [f"page={page}", f"rating_method={rating_method}"]
            if query:
                redirect_params.append(f"query={query}")
            if selected_rating_movie_id:
                redirect_params.append(f"selected_rating_movie_id={selected_rating_movie_id}")
            if explore_count is not None:
                redirect_params.append(f"explore_count={explore_count}")
            if explored_movie_ids:
                redirect_params.append(f"explored_movie_ids={explored_movie_ids}")
            return RedirectResponse(url=f"/?{'&'.join(redirect_params)}", status_code=303)
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
    current_user = get_current_user_from_cookies(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자 정보가 올바르지 않습니다.")

    try:
        conn_obj = get_user_manager()
        # DELETE from custom_ratings
        import psycopg2
        from core.user_system.db_manager import _connect
        conn = _connect()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM custom_ratings WHERE user_id = %s AND movie_id = %s",
                    (user_id, movie_id),
                )
        conn.close()
        conn_obj.log_activity(user_id, "delete_rating", {"movie_id": movie_id})
        return RedirectResponse(url=f"/?page={page}", status_code=303)

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
    try:
        df_movies = load_movie_data()
        popular_ids = get_popular_movie_ids(200)
        random_movies, _ = get_random_popular_movies(
            popular_movie_ids=popular_ids, df_movies=df_movies, n_movies=explore_count, exclude_movie_ids=None
        )

        if not random_movies.empty:
            explored_movie_ids = ",".join(random_movies["movie_id"].astype(str).tolist())
            redirect_url = f"/?page={page}&rating_method={rating_method}&explore_count={explore_count}&explored_movie_ids={explored_movie_ids}"
        else:
            redirect_url = f"/?page={page}&rating_method={rating_method}&explore_count={explore_count}"

        return RedirectResponse(url=redirect_url, status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"탐색 실패: {str(e)}")
