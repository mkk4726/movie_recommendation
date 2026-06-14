"""
Activity logging API endpoints.
"""

import logging

from fastapi import APIRouter, Body, HTTPException, Request

from app.api.schemas import ClickEventRequest
from app.api.utils import log_click_activity

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/activity/click", status_code=201)
async def log_click_event(request: Request, click_event: ClickEventRequest = Body(...)):
    """
    클릭 이벤트 로깅

    검색 결과나 추천 결과에서 영화를 클릭했을 때 호출됩니다.
    """
    try:
        log_click_activity(
            request,
            session_id=click_event.session_id,
            movie_id=click_event.movie_id,
            position=click_event.position,
            search_query=click_event.search_query,
            link_type=click_event.link_type,
        )

        logger.info(
            "✅ 클릭 로깅 완료: session=%s, movie=%s, pos=%s, type=%s",
            click_event.session_id,
            click_event.movie_id,
            click_event.position,
            click_event.link_type,
        )

        return {"status": "success", "message": "Click event logged successfully"}

    except Exception as e:
        logger.error(f"클릭 로깅 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"클릭 로깅 중 오류가 발생했습니다: {str(e)}")
