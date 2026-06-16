"""
포스터 검색 파이프라인 싱글톤 캐시.
"""

from functools import lru_cache

from core.pipelines.poster_search import PosterSearchPipeline


class ClipServiceError(Exception):
    """포스터 검색 서비스 오류 (하위 호환)"""
    pass


@lru_cache(maxsize=1)
def get_poster_search_pipeline() -> PosterSearchPipeline:
    return PosterSearchPipeline()
