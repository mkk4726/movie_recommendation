"""
FastAPI application main file.
Creates the FastAPI app and registers all route routers.
"""
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from modules.core import add_project_paths
from app.api.routes import health, movies, users, auth, ratings, home

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 lifespan 이벤트"""
    # 시작 시
    logger.info("=" * 80)
    logger.info("🚀 FastAPI 애플리케이션 시작 중...")
    logger.info("=" * 80)
    
    # 모델 사전 로드
    try:
        logger.info("📦 추천 모델 사전 로드 시작...")
        from modules.services.recommender_service import get_recommender_service
        recommender_service = get_recommender_service()
        logger.info("✅ 모든 모델 로드 완료")
    except Exception as e:
        logger.error(f"❌ 모델 로드 중 오류 발생: {e}", exc_info=True)
        raise
    
    # 데이터 사전 로드
    try:
        logger.info("📦 데이터 사전 로드 시작...")
        from modules.services.data_access import load_all_data
        df_movies, df_ratings, df_filtered = load_all_data()
        logger.info(f"✅ 데이터 로드 완료: 영화 {len(df_movies)}개, 평점 {len(df_ratings)}개")
    except Exception as e:
        logger.error(f"❌ 데이터 로드 중 오류 발생: {e}", exc_info=True)
        raise
    
    logger.info("=" * 80)
    logger.info("🎉 모든 모델 및 데이터 캐시 로드 완료!")
    logger.info("✅ FastAPI 서버 준비 완료 - 요청 대기 중...")
    logger.info("=" * 80)
    
    yield
    
    # 종료 시
    logger.info("👋 FastAPI 애플리케이션 종료 중...")


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
app.include_router(home.router)

