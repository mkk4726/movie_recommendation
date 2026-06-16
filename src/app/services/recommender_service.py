"""
추천 파이프라인 싱글톤 캐시.
"""

from functools import lru_cache

from core.pipelines.user_cf import UserCFPipeline
from core.pipelines.item_cf import ItemCFPipeline


@lru_cache(maxsize=1)
def get_user_cf_pipeline() -> UserCFPipeline:
    return UserCFPipeline()


@lru_cache(maxsize=1)
def get_item_cf_pipeline() -> ItemCFPipeline:
    return ItemCFPipeline()
