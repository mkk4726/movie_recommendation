"""
FastAPI lifespan: startup loading and shutdown logic.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.app_state import set_loading, set_progress

logger = logging.getLogger(__name__)


def _load_models_sync():
    set_loading(True, "📦 추천 모델 로딩 중...")
    logger.info("📦 추천 모델 사전 로드 시작...")
    from app.services.recommender_service import get_user_cf_pipeline, get_item_cf_pipeline

    get_user_cf_pipeline()._ensure_loaded()
    get_item_cf_pipeline()._ensure_loaded()
    set_progress("model", True)
    logger.info("✅ 모든 모델 로드 완료")


def _load_data_sync():
    set_loading(True, "📦 데이터 로딩 중...")
    logger.info("📦 데이터 사전 로드 시작...")
    from core.db.data_access import load_movie_data, get_popular_movie_ids, load_cast_data

    df_movies = load_movie_data()
    logger.info(f"✅ 영화 데이터 로드 완료: 영화 {len(df_movies)}개")

    logger.info("📊 인기 영화 목록 캐싱 중...")
    get_popular_movie_ids(200)
    logger.info("✅ 인기 영화 목록 캐싱 완료")

    try:
        load_cast_data()
    except Exception as e:
        logger.warning(f"⚠️ Cast 데이터 로드 실패 (계속 진행): {e}")

    set_progress("data", True)
    logger.info("✅ 모든 데이터 로드 완료")


def _load_search_pipeline_sync():
    set_loading(True, "🔍 검색 파이프라인 로딩 중...")
    logger.info("🔍 검색 파이프라인 사전 로드 시작...")
    from app.api.routes.search import get_search_pipeline

    try:
        get_search_pipeline()._ensure_loaded()
        set_progress("search", True)
        logger.info("✅ 검색 파이프라인 로드 완료")
    except Exception as e:
        logger.error(f"❌ 검색 파이프라인 로드 실패: {e}", exc_info=True)


def _load_poster_search_pipeline_sync():
    set_loading(True, "🖼️ 포스터 검색 파이프라인 로딩 중...")
    logger.info("🖼️ 포스터 검색 파이프라인 사전 로드 시작...")
    from app.services.clip_service import get_poster_search_pipeline

    try:
        pipeline = get_poster_search_pipeline()
        pipeline._ensure_clip_loaded()

        # CLIP 내부 파이프라인 사전 로드 (언어 감지/번역 포함)
        if pipeline._clip is not None:
            if hasattr(pipeline._clip, "_ensure_loaded"):
                pipeline._clip._ensure_loaded()
            if hasattr(pipeline._clip, "_load_language_modules"):
                logger.info("🔄 언어 감지 및 번역 모듈 사전 로드 중...")
                pipeline._clip._load_language_modules()
                logger.info("✅ 언어 감지 및 번역 모듈 사전 로드 완료")

        set_progress("poster_search", True)
        logger.info("✅ 포스터 검색 파이프라인 로드 완료")
    except Exception as e:
        logger.error(f"❌ 포스터 검색 파이프라인 로드 실패: {e}", exc_info=True)


async def _run_loader(fn, *, fatal: bool = False) -> bool:
    try:
        await asyncio.get_running_loop().run_in_executor(None, fn)
        return True
    except Exception as e:
        logger.error(f"❌ {fn.__name__} 실패: {e}", exc_info=True)
        if fatal:
            set_loading(False, f"{fn.__name__} 실패")
        return False


async def _load_all():
    set_loading(True, "애플리케이션 초기화 중...")

    if not await _run_loader(_load_models_sync, fatal=True):
        return
    if not await _run_loader(_load_data_sync, fatal=True):
        return

    await _run_loader(_load_search_pipeline_sync)
    await _run_loader(_load_poster_search_pipeline_sync)

    set_loading(False, "준비 완료")

    logger.info("=" * 80)
    logger.info("🎉 모든 모델 및 데이터 캐시 로드 완료!")
    logger.info("✅ FastAPI 서버 준비 완료 - 요청 대기 중...")
    logger.info("⏱️  백그라운드 로딩 완료 시각: %s", __import__("datetime").datetime.now().strftime("%H:%M:%S"))
    logger.info("=" * 80)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 80)
    logger.info("🚀 FastAPI 애플리케이션 시작 중...")
    logger.info("=" * 80)

    set_loading(True, "애플리케이션 초기화 중...")
    load_task = asyncio.create_task(_load_all())

    yield

    logger.info("👋 FastAPI 애플리케이션 종료 중...")
    if not load_task.done():
        load_task.cancel()
        try:
            await load_task
        except asyncio.CancelledError:
            pass
