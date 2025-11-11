"""
Natural Language Search API endpoints using QuerySearchPipeline.
자연어 검색 파이프라인 - BM25 기반 검색을 사용하여 영화를 검색합니다.
"""
import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

from modules.services.data_access import load_all_data
from app.api.models import QuerySearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# QuerySearchPipeline 전역 변수 (지연 로딩)
_search_pipeline = None
_search_pipeline_error = None


def get_search_pipeline():
    """QuerySearchPipeline을 지연 로딩합니다."""
    global _search_pipeline, _search_pipeline_error
    
    if _search_pipeline is not None:
        return _search_pipeline
    
    if _search_pipeline_error is not None:
        raise _search_pipeline_error
    
    try:
        logger.info("🔄 QuerySearchPipeline 로딩 중...")
        
        # modeling/models/config.yaml 경로 찾기
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "modeling" / "models" / "config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"검색 설정 파일을 찾을 수 없습니다: {config_path}")
        
        # QuerySearchPipeline import 및 초기화
        query_search_path = str(project_root / "modeling" / "models")
        if query_search_path not in sys.path:
            sys.path.insert(0, query_search_path)
        
        from query_search import QuerySearchPipeline  # type: ignore
        
        # 영화 데이터 로드
        df_movies, _, _ = load_all_data()
        logger.info(f"📊 영화 데이터 로드 완료: {len(df_movies)}개")
        
        # 파이프라인 생성 및 학습
        _search_pipeline = QuerySearchPipeline(yaml_path=str(config_path))
        _search_pipeline.fit(df_movies)
        
        logger.info("✅ QuerySearchPipeline 로딩 완료")
        return _search_pipeline
        
    except Exception as e:
        logger.error(f"❌ QuerySearchPipeline 로딩 실패: {e}", exc_info=True)
        _search_pipeline_error = e
        raise HTTPException(
            status_code=500,
            detail=f"검색 파이프라인 로딩 실패: {str(e)}"
        )


@router.get("/search/natural-language", response_model=QuerySearchResponse)
def natural_language_search(
    query: str = Query(..., min_length=1, description="자연어 검색 쿼리"),
    limit: int = Query(20, ge=1, le=100, description="반환할 최대 결과 수"),
    min_score: float = Query(0.0, ge=0.0, description="최소 검색 스코어 임계값"),
):
    """
    자연어 검색 API (BM25 기반)
    
    QuerySearchPipeline을 사용하여 자연어 쿼리로 영화를 검색합니다.
    BM25 알고리즘을 사용하여 제목, 장르, 줄거리 등에서 관련 영화를 찾습니다.
    
    예시:
    - "toy story animation"
    - "action movies with robots"
    - "romantic comedy 2020"
    - "thriller directed by christopher nolan"
    """
    try:
        # 1. QuerySearchPipeline 로드
        pipeline = get_search_pipeline()
        
        # 2. 검색 실행 (Pydantic 모델 반환)
        logger.info(f"🔍 자연어 검색: '{query}' (limit={limit}, min_score={min_score})")
        response = pipeline.search_to_response(
            query=query,
            top_k=limit,
            min_score=min_score
        )
        
        logger.info(f"✅ 검색 완료: {response.total_results}개 결과")
        return response
        
    except FileNotFoundError as exc:
        logger.error(f"파일을 찾을 수 없습니다: {exc}")
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"자연어 검색 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"자연어 검색 중 오류가 발생했습니다: {str(exc)}"
        )
