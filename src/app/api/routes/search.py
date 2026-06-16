"""
자연어 검색 API (BM25 기반).
"""

import logging
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import QuerySearchResponse
from app.api.utils import log_search_activity
from core.pipelines.natural_language import NaturalLanguageSearchPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

_pipeline_error: Exception | None = None


@lru_cache(maxsize=1)
def get_search_pipeline() -> NaturalLanguageSearchPipeline:
    return NaturalLanguageSearchPipeline()


@router.get("/search/natural-language", response_model=QuerySearchResponse)
def natural_language_search(
    request: Request,
    query: str = Query(..., min_length=1, description="자연어 검색 쿼리"),
    limit: int = Query(20, ge=1, le=100, description="반환할 최대 결과 수"),
    min_score: float = Query(0.0, ge=0.0, description="최소 검색 스코어 임계값"),
    min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점"),
    min_vote_count: int = Query(0, ge=0, description="최소 평가 수"),
    genre: Optional[List[str]] = Query(None, description="장르 필터"),
    language: Optional[List[str]] = Query(None, description="언어 필터"),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
):
    """자연어 검색 API (BM25 기반)"""
    try:
        pipeline = get_search_pipeline()
        logger.info(f"🔍 자연어 검색: '{query}'")
        response = pipeline.search(
            query=query,
            top_k=limit,
            min_score=min_score,
            min_rating=min_rating,
            min_vote_count=min_vote_count,
            genre_filter=genre,
            language_filter=language,
            include_cast=include_cast,
        )

        filters = {"min_rating": min_rating, "min_vote_count": min_vote_count, "genre": genre, "language": language}
        result_movie_ids = [r.movie_id for r in response.results]
        session_id = log_search_activity(
            request,
            query=query,
            result_count=response.total_results,
            result_movie_ids=result_movie_ids,
            search_type="natural_language",
            filters=filters,
        )
        response.session_id = session_id

        logger.info(f"✅ 검색 완료: {response.total_results}개 결과")
        return response

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"자연어 검색 실패: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"자연어 검색 중 오류가 발생했습니다: {str(exc)}")
