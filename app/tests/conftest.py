"""
pytest 설정 및 공통 fixture
"""
import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import load_movie_data, load_ratings_data, filter_data


@pytest.fixture(scope="session")
def df_movies():
    """영화 데이터 fixture (세션 전체에서 한 번만 로드)"""
    return load_movie_data()


@pytest.fixture(scope="session")
def df_ratings():
    """평점 데이터 fixture (세션 전체에서 한 번만 로드)"""
    return load_ratings_data()


@pytest.fixture(scope="session")
def df_ratings_filtered(df_ratings):
    """필터링된 평점 데이터 fixture"""
    return filter_data(df_ratings, min_user_ratings=30, min_movie_ratings=10)

