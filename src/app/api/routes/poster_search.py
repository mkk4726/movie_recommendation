"""
포스터 의미 검색 API (CLIP 기반).
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import PosterSearchResponse, PosterSearchResultMovie
from app.api.utils import log_search_activity
from app.services.clip_service import ClipServiceError, get_poster_search_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search/poster", response_model=PosterSearchResponse)
def poster_search_by_text(
    request: Request,
    query: str = Query(..., min_length=1, description="텍스트 검색 쿼리 (영어 또는 한국어)"),
    limit: int = Query(10, ge=1, le=50, description="반환할 최대 결과 수"),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
    min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점"),
    min_vote_count: int = Query(0, ge=0, description="최소 평가 수"),
    genre: Optional[List[str]] = Query(None, description="장르 필터"),
    language: Optional[List[str]] = Query(None, description="언어 필터"),
):
    """텍스트로 포스터 검색 API (CLIP 기반)"""
    try:
        pipeline = get_poster_search_pipeline()

        filters = {}
        if min_rating > 0:
            filters["min_rating"] = min_rating
        if min_vote_count > 0:
            filters["min_vote_count"] = min_vote_count
        if genre:
            filters["genre"] = genre
        if language:
            filters["language"] = language

        logger.info(f"🔍 포스터 검색: '{query}' (limit={limit})")
        raw_results = pipeline.search(
            query=query,
            top_k=limit,
            filters=filters or None,
            include_cast=include_cast,
        )

        if not raw_results and filters:
            return PosterSearchResponse(query_type="text", query=query, total_results=0, results=[], session_id=None)

        enriched = [PosterSearchResultMovie(**r) for r in raw_results]

        result_movie_ids = [r.movie_id for r in enriched]
        session_id = log_search_activity(
            request,
            query=query,
            result_count=len(enriched),
            result_movie_ids=result_movie_ids,
            search_type="poster",
            filters={"min_rating": min_rating, "min_vote_count": min_vote_count, "genre": genre, "language": language},
        )

        response = PosterSearchResponse(
            query_type="text",
            query=query,
            total_results=len(enriched),
            results=enriched,
            session_id=session_id,
        )

        logger.info(f"✅ 포스터 검색 완료: {response.total_results}개 결과")
        return response

    except ClipServiceError as exc:
        raise HTTPException(status_code=503, detail=f"포스터 검색 서비스를 사용할 수 없습니다: {str(exc)}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"포스터 검색 실패: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"포스터 검색 중 오류가 발생했습니다: {str(exc)}")
