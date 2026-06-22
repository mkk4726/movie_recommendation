"""
FastAPI application entry point.
Creates the app and registers all route routers.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드 완료: {env_path}")
else:
    print(f"⚠️ .env 파일을 찾을 수 없습니다: {env_path}")

from app.api.lifespan import lifespan
from app.api.middleware import StartupReadinessMiddleware
from app.api.routes import activity, auth, health, home, movies, poster_search, ratings, search, users

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Movie Recommendation Backend",
    description="FastAPI service that wraps the existing recommendation models.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(StartupReadinessMiddleware)

BASE_DIR = Path(__file__).parent.parent
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(ratings.router)
app.include_router(search.router)
app.include_router(poster_search.router)
app.include_router(home.router)
app.include_router(activity.router)
