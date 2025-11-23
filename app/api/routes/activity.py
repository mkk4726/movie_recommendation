"""
Activity logging and click tracking API endpoints.
"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from app.api.models import ClickEventRequest, CTRDataPoint, ActivityStats
from app.api.user_activity_logger import get_activity_logger

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/activity/click", status_code=201)
async def log_click_event(
    request: Request,
    click_event: ClickEventRequest = Body(...)
):
    """
    클릭 이벤트 로깅
    
    검색 결과나 추천 결과에서 영화를 클릭했을 때 호출됩니다.
    CTR 분석을 위해 검색 세션과 연결됩니다.
    """
    try:
        activity_logger = get_activity_logger()
        
        # 클릭 이벤트 로깅
        activity_logger.log_click(
            request=request,
            session_id=click_event.session_id,
            movie_id=click_event.movie_id,
            position=click_event.position,
            search_query=click_event.search_query
        )
        
        logger.info(f"✅ 클릭 로깅 완료: session={click_event.session_id}, movie={click_event.movie_id}, pos={click_event.position}")
        
        return {
            "status": "success",
            "message": "Click event logged successfully"
        }
        
    except Exception as e:
        logger.error(f"클릭 로깅 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"클릭 로깅 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/activity/ctr-data", response_model=List[CTRDataPoint])
async def get_ctr_data(
    ip_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    CTR 분석 데이터 조회
    
    검색-클릭 쌍 데이터를 반환합니다.
    CTR 예측 모델 학습에 활용할 수 있습니다.
    """
    try:
        activity_logger = get_activity_logger()
        
        # 날짜 파싱
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # CTR 데이터 조회
        ctr_data = activity_logger.get_ctr_data(
            ip_filter=ip_filter,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # Pydantic 모델로 변환
        result = [CTRDataPoint(**data) for data in ctr_data]
        
        logger.info(f"✅ CTR 데이터 조회 완료: {len(result)}개")
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 날짜 형식입니다: {str(e)}"
        )
    except Exception as e:
        logger.error(f"CTR 데이터 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"CTR 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/activity/stats", response_model=ActivityStats)
async def get_activity_stats(ip: Optional[str] = None):
    """
    활동 통계 조회
    
    검색, 클릭, 평점, 조회 등의 활동 통계를 반환합니다.
    IP 필터를 지정하면 특정 사용자의 통계만 조회합니다.
    """
    try:
        activity_logger = get_activity_logger()
        
        # 통계 조회
        stats = activity_logger.get_stats(ip=ip)
        
        logger.info(f"✅ 활동 통계 조회 완료: {stats}")
        return ActivityStats(**stats)
        
    except Exception as e:
        logger.error(f"활동 통계 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"활동 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
