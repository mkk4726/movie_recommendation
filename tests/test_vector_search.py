"""
Vector Store 검색 테스트

FAISS 인덱스를 로드하고 다양한 검색 테스트를 수행합니다.
"""

import sys
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
import pytest
import requests
from PIL import Image

# 프로젝트 루트를 sys.path에 추가하여 src 모듈을 임포트할 수 있도록 설정
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import matplotlib

from src.data_scraping.common import load_movie_data
from src.modeling.models.clip.models.base import BaseClipEncoder
from src.vector_store import FAISSManager, load_config

matplotlib.use("Agg")  # GUI 없이 이미지 생성


@pytest.fixture(scope="module")
def config():
    """설정 파일 로드"""
    return load_config()


@pytest.fixture(scope="module")
def faiss_manager(config):
    """FAISS 매니저 초기화"""
    manager = FAISSManager(config=config)
    manager.load()
    return manager


@pytest.fixture(scope="module")
def clip_encoder():
    """CLIP 인코더 초기화"""
    try:
        return BaseClipEncoder(model_key="jina-clip")
    except Exception:
        pytest.skip("CLIP 인코더를 로드할 수 없습니다.")


@pytest.fixture(scope="module")
def movie_data():
    """영화 데이터 로드"""
    try:
        df = load_movie_data()
        return df
    except Exception as e:
        pytest.skip(f"영화 데이터 로드 실패: {e}")


@pytest.fixture(scope="module")
def movie_ids(config):
    """movie_ids 매핑 로드"""
    import json

    base_dir_str = config["index"]["base_dir"]
    base_dir = Path(base_dir_str)

    if not base_dir.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        base_dir = project_root / base_dir

    movie_ids_path = base_dir / "movie_ids.json"

    if not movie_ids_path.exists():
        pytest.skip(f"movie_ids.json 파일을 찾을 수 없습니다: {movie_ids_path}")

    with open(movie_ids_path) as f:
        return json.load(f)


class TestVectorSearch:
    """벡터 검색 테스트 클래스"""

    def test_faiss_manager_loaded(self, faiss_manager, config):
        """FAISS 매니저가 올바르게 로드되었는지 확인"""
        assert faiss_manager is not None
        assert faiss_manager.total_vectors > 0
        assert faiss_manager.index is not None

    def test_random_vector_search(self, faiss_manager, config):
        """랜덤 벡터로 검색 성능 테스트"""
        k = 10
        vector_dim = config["vector"]["dim"]

        # 랜덤 쿼리 벡터 생성 (정규화)
        query_vector = np.random.randn(vector_dim).astype("float32")
        query_vector = query_vector / np.linalg.norm(query_vector)

        # 검색 수행
        results = faiss_manager.search(query_vector, k=k)

        # 검증
        assert len(results) == k
        assert all("index" in r for r in results)
        assert all("score" in r for r in results)
        assert all(isinstance(r["index"], (int, np.integer)) for r in results)
        assert all(isinstance(r["score"], (float, np.floating)) for r in results)

    def test_search_result_order(self, faiss_manager, config):
        """검색 결과가 점수 순으로 정렬되는지 확인"""
        k = 10
        vector_dim = config["vector"]["dim"]

        query_vector = np.random.randn(vector_dim).astype("float32")
        query_vector = query_vector / np.linalg.norm(query_vector)

        results = faiss_manager.search(query_vector, k=k)
        scores = [r["score"] for r in results]

        # 거리 메트릭에 따라 정렬 순서 확인
        metric = config["vector"]["distance_metric"]
        if metric.lower() in ["cosine", "inner_product"]:
            # 높은 점수가 더 유사 (내림차순)
            assert scores == sorted(scores, reverse=True)
        else:
            # 낮은 거리가 더 유사 (오름차순)
            assert scores == sorted(scores)

    def test_batch_search_performance(self, faiss_manager, config):
        """배치 검색 성능 테스트"""
        batch_size = 10
        k = 10
        vector_dim = config["vector"]["dim"]

        # 배치 쿼리 벡터 생성
        vectors = np.random.randn(batch_size, vector_dim).astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        query_vectors = vectors / norms

        # 배치 검색 수행
        for query_vector in query_vectors:
            results = faiss_manager.search(query_vector, k=k)
            assert len(results) == k

    def test_index_statistics(self, faiss_manager, config):
        """인덱스 통계 정보 검증"""
        assert faiss_manager.total_vectors > 0
        assert config["vector"]["dim"] > 0
        assert config["vector"]["distance_metric"] in [
            "cosine",
            "inner_product",
            "l2",
            "euclidean",
        ]

        # 인덱스 파일 존재 확인
        index_path = faiss_manager.index_path
        assert index_path is not None
        assert index_path.exists()
        assert index_path.stat().st_size > 0


class TestSearchHelpers:
    """검색 헬퍼 함수 테스트"""

    @staticmethod
    def get_poster_urls(faiss_indices, movie_ids, movie_df):
        """인덱스 리스트로부터 포스터 URL 가져오기"""
        poster_urls = []
        for faiss_idx in faiss_indices:
            if faiss_idx < len(movie_ids):
                movie_id = movie_ids[faiss_idx]

                # movie_id 타입 변환
                if len(movie_df) > 0:
                    df_movie_id_type = type(movie_df.iloc[0]["movie_id"])
                    if df_movie_id_type is str and not isinstance(movie_id, str):
                        movie_id = str(movie_id)
                    elif df_movie_id_type is int and not isinstance(movie_id, int):
                        movie_id = int(movie_id)

                movie_row = movie_df[movie_df["movie_id"] == movie_id]

                if not movie_row.empty:
                    import pandas as pd

                    poster_path = movie_row.iloc[0].get("poster_path")
                    if poster_path and pd.notna(poster_path):
                        poster_url = f"https://image.tmdb.org/t/p/w300/{poster_path}"
                        poster_urls.append(poster_url)
                    else:
                        poster_urls.append(None)
                else:
                    poster_urls.append(None)
            else:
                poster_urls.append(None)

        return poster_urls

    @staticmethod
    def download_image(url: str, timeout: int = 5) -> Optional[Image.Image]:
        """URL에서 이미지 다운로드"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
        except Exception:
            pass
        return None
