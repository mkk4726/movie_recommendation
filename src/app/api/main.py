"""
FastAPI application main file.
Creates the FastAPI app and registers all route routers.
"""
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드 완료: {env_path}")
else:
    print(f"⚠️ .env 파일을 찾을 수 없습니다: {env_path}")

from modules.core import add_project_paths
from app.api.routes import health, movies, users, auth, ratings, home, search, poster_search
from app.api.app_state import set_loading, set_progress

# Firebase 관련 import (선택적)
try:
    from user_system.firebase_config import setup_firebase_config
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

add_project_paths()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def _load_models_sync():
    """동기 함수로 모델 로드"""
    set_loading(True, "📦 추천 모델 로딩 중...")
    logger.info("📦 추천 모델 사전 로드 시작...")
    from modules.services.recommender_service import get_recommender_service
    recommender_service = get_recommender_service()
    set_progress("model", True)
    logger.info("✅ 모든 모델 로드 완료")


def _load_data_sync():
    """동기 함수로 데이터 로드"""
    set_loading(True, "📦 데이터 로딩 중...")
    logger.info("📦 데이터 사전 로드 시작...")
    from modules.services.data_access import load_all_data
    from app.api.routes.poster_search import get_cast_data
    
    df_movies, df_ratings, df_filtered = load_all_data()
    logger.info(f"✅ 영화/평점 데이터 로드 완료: 영화 {len(df_movies)}개, 평점 {len(df_ratings)}개")
    
    # Cast 데이터 로드 및 인덱싱
    try:
        get_cast_data()  # 전역 캐시를 사용하여 로드 및 인덱싱
    except Exception as e:
        logger.warning(f"⚠️ Cast 데이터 로드 실패 (계속 진행): {e}")
    
    set_progress("data", True)
    logger.info("✅ 모든 데이터 로드 완료")


def _load_search_pipeline_sync():
    """동기 함수로 검색 파이프라인 로드"""
    set_loading(True, "🔍 검색 파이프라인 로딩 중...")
    logger.info("🔍 검색 파이프라인 사전 로드 시작...")
    from app.api.routes.search import get_search_pipeline
    try:
        get_search_pipeline()
        set_progress("search", True)
        logger.info("✅ 검색 파이프라인 로드 완료")
    except Exception as e:
        logger.error(f"❌ 검색 파이프라인 로드 실패: {e}", exc_info=True)


def _load_poster_search_pipeline_sync():
    """동기 함수로 포스터 검색 파이프라인 로드"""
    set_loading(True, "🖼️ 포스터 검색 파이프라인 로딩 중...")
    logger.info("🖼️ 포스터 검색 파이프라인 사전 로드 시작...")
    from app.modules.services.clip_service import get_clip_search_service
    try:
        clip_service = get_clip_search_service()
        # 파이프라인을 실제로 로드하기 위해 _ensure_loaded 호출
        clip_service._ensure_loaded()
        # 파이프라인 내부의 인코더, FAISS, movie_ids도 미리 로드
        if clip_service.pipeline is not None:
            clip_service.pipeline._ensure_loaded()
            logger.info("✅ CLIP 인코더, FAISS 인덱스, movie_ids 사전 로드 완료")
            
            # 언어 감지 및 번역 모듈 미리 로드
            logger.info("🔄 언어 감지 및 번역 모듈 사전 로드 중...")
            clip_service.pipeline._load_language_modules()
            logger.info("✅ 언어 감지 및 번역 모듈 사전 로드 완료")
        
        set_progress("poster_search", True)
        logger.info("✅ 포스터 검색 파이프라인 로드 완료")
    except Exception as e:
        logger.error(f"❌ 포스터 검색 파이프라인 로드 실패: {e}", exc_info=True)


async def load_models_and_data():
    """백그라운드에서 모델과 데이터를 로드하는 함수"""
    # 로딩 상태 시작
    set_loading(True, "애플리케이션 초기화 중...")
    
    # 모델 사전 로드 (비동기 스레드에서 실행)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_models_sync)
    except Exception as e:
        logger.error(f"❌ 모델 로드 중 오류 발생: {e}", exc_info=True)
        set_loading(False, "모델 로드 실패")
        return
    
    # 데이터 사전 로드 (비동기 스레드에서 실행)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_data_sync)
    except Exception as e:
        logger.error(f"❌ 데이터 로드 중 오류 발생: {e}", exc_info=True)
        set_loading(False, "데이터 로드 실패")
        return
    
    # 검색 파이프라인 사전 로드 (비동기 스레드에서 실행)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_search_pipeline_sync)
    except Exception as e:
        logger.error(f"❌ 검색 파이프라인 로드 중 오류 발생: {e}", exc_info=True)
        # 검색 파이프라인 로드 실패는 치명적이지 않으므로 계속 진행
    
    # 포스터 검색 파이프라인 사전 로드 (비동기 스레드에서 실행)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_poster_search_pipeline_sync)
    except Exception as e:
        logger.error(f"❌ 포스터 검색 파이프라인 로드 중 오류 발생: {e}", exc_info=True)
        # 포스터 검색 파이프라인 로드 실패는 치명적이지 않으므로 계속 진행
    
    # 로딩 완료
    set_loading(False, "준비 완료")
    
    logger.info("=" * 80)
    logger.info("🎉 모든 모델 및 데이터 캐시 로드 완료!")
    logger.info("✅ FastAPI 서버 준비 완료 - 요청 대기 중...")
    logger.info("⏱️  백그라운드 로딩 완료 시각: %s", __import__('datetime').datetime.now().strftime("%H:%M:%S"))
    logger.info("=" * 80)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 lifespan 이벤트"""
    # 시작 시
    logger.info("=" * 80)
    logger.info("🚀 FastAPI 애플리케이션 시작 중...")
    logger.info("=" * 80)
    
    # 로딩 상태 시작 (요청을 받을 수 있도록 먼저 설정)
    set_loading(True, "애플리케이션 초기화 중...")
    
    # 백그라운드 태스크로 로딩 시작 (요청을 받을 수 있도록 yield 전에 태스크 생성)
    load_task = asyncio.create_task(load_models_and_data())
    
    # yield를 먼저 실행해서 서버가 요청을 받을 수 있게 함
    yield
    
    # 종료 시
    logger.info("👋 FastAPI 애플리케이션 종료 중...")
    
    # 로딩 태스크 취소 (아직 완료되지 않았다면)
    if not load_task.done():
        load_task.cancel()
        try:
            await load_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Movie Recommendation Backend",
    description="FastAPI service that wraps the existing recommendation models.",
    version="0.1.0",
    lifespan=lifespan,
)

# Static files
BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Firebase 초기화 (앱 시작 시)
if FIREBASE_AVAILABLE:
    try:
        setup_firebase_config()
    except Exception as e:
        print(f"Firebase 초기화 실패: {e}")

# Register routers
app.include_router(health.router)
app.include_router(movies.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(ratings.router)
app.include_router(search.router)
app.include_router(poster_search.router)
app.include_router(home.router)

# Activity logging router
try:
    from app.api.routes import activity
    app.include_router(activity.router)
except ImportError:
    logger.warning("Activity logging router not available")
