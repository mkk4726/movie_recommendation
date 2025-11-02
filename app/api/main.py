"""
FastAPI application main file.
Creates the FastAPI app and registers all route routers.
"""
from pathlib import Path
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

app = FastAPI(
    title="Movie Recommendation Backend",
    description="FastAPI service that wraps the existing recommendation models.",
    version="0.1.0",
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

