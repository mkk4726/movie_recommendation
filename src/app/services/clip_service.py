"""
CLIP Service for Poster Search

텍스트로 포스터를 검색하기 위한 CLIP 파이프라인 관리 서비스
"""

import logging
from functools import lru_cache
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# CLIP 파이프라인 전역 변수 (지연 로딩)
_text_to_poster_pipeline = None
_clip_service_error = None


class ClipServiceError(Exception):
    """CLIP 서비스 관련 오류"""

    pass


def get_text_to_poster_pipeline():
    """TextToPosterSearchPipeline을 지연 로딩합니다."""
    global _text_to_poster_pipeline, _clip_service_error

    if _text_to_poster_pipeline is not None:
        return _text_to_poster_pipeline

    if _clip_service_error is not None:
        raise _clip_service_error

    try:
        logger.info("🔄 TextToPosterSearchPipeline 로딩 중...")

        from core.modeling.models.clip.text_to_poster_search import TextToPosterSearchPipeline
        from core.vector_store.utils.config import get_clip_enable_translation, get_clip_model_key, load_config

        config = load_config()
        model_key = get_clip_model_key(config)
        enable_translation = get_clip_enable_translation(config)

        # 파이프라인 생성
        _text_to_poster_pipeline = TextToPosterSearchPipeline(
            model_key=model_key,
            enable_translation=enable_translation,
        )

        logger.info(f"✅ TextToPosterSearchPipeline 로드 완료 (model={model_key}, translation={enable_translation})")
        return _text_to_poster_pipeline

    except Exception as e:
        logger.error(f"❌ TextToPosterSearchPipeline 로딩 실패: {e}", exc_info=True)
        _clip_service_error = ClipServiceError(f"TextToPosterSearchPipeline 로딩 실패: {str(e)}")
        raise _clip_service_error


class ClipSearchService:
    """CLIP 기반 포스터 검색 서비스"""

    def __init__(self):
        """서비스 초기화 (실제 로딩은 지연 로딩)"""
        self.pipeline = None

    def _ensure_loaded(self):
        """필요한 리소스가 로드되었는지 확인하고 로드"""
        if self.pipeline is None:
            self.pipeline = get_text_to_poster_pipeline()

    def search_by_text(
        self,
        text: str,
        k: int = 10,
        filter_movie_ids: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        텍스트 쿼리로 포스터 검색

        Args:
            text: 검색 텍스트
            k: 반환할 결과 수
            filter_movie_ids: 검색 대상 영화 ID 리스트 (None이면 전체 검색)

        Returns:
            검색 결과 리스트 [{"movie_id": str, "score": float, "index": int}, ...]
        """
        self._ensure_loaded()

        logger.info(
            f"🔍 텍스트-포스터 검색: '{text}' (k={k}, filter_ids={len(filter_movie_ids) if filter_movie_ids else 'None'})"
        )

        # 파이프라인으로 검색
        results = self.pipeline.search(query=text, top_k=k, filter_movie_ids=filter_movie_ids)

        logger.info(f"✅ 텍스트-포스터 검색 완료: {len(results)}개 결과")
        return results


@lru_cache(maxsize=1)
def get_clip_search_service() -> ClipSearchService:
    """ClipSearchService 싱글톤 인스턴스를 반환합니다."""
    return ClipSearchService()
