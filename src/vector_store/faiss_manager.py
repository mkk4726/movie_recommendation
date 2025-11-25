"""
FAISS Manager

FAISS 인덱스를 관리하고 유사도 검색을 수행하는 클래스
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError("FAISS is not installed. Please install it with: pip install faiss-cpu")

from .utils.config import get_embeddings_path, get_index_path, load_config

logger = logging.getLogger(__name__)


class FAISSManager:
    """FAISS 벡터 인덱스 관리 클래스"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            config: 벡터 저장소 설정. None이면 기본 설정 사용
        """
        self.config = config or load_config()
        self.index: Optional[faiss.Index] = None
        self._loaded = False

        logger.info(f"FAISSManager initialized with config: {self.config}")

    def load(self) -> None:
        """FAISS 인덱스 로드"""
        if self._loaded:
            logger.warning("Index already loaded")
            return

        # 인덱스 로드
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Index file not found: {self.index_path}\nPlease build the index first using build_index.py"
            )

        logger.info(f"Loading FAISS index from {self.index_path}")
        self.index = faiss.read_index(str(self.index_path))
        logger.info(f"Index loaded: {self.index.ntotal} vectors")

        self._loaded = True

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        allowed_indices: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색 수행

        Args:
            query_vector: 쿼리 벡터 (shape: (512,) or (1, 512))
            k: 반환할 결과 수
            allowed_indices: 검색 허용할 인덱스 집합 (None이면 전체 검색)

        Returns:
            검색 결과 리스트 (score 내림차순)
        """
        if not self._loaded:
            self.load()

        # 벡터 전처리
        query_vector = self._preprocess_query(query_vector)

        # 검색 개수 설정
        search_multiplier = self.config["search"]["search_multiplier"]
        search_k = k * search_multiplier

        # 필터링이 있는 경우 검색 범위를 전체로 확장하여 100% 보장
        if allowed_indices is not None:
            # 필터링된 결과 중에서 상위 k개를 확실히 찾기 위해 전체 검색 수행
            # 데이터 규모(수만 건)가 크지 않아 전체 검색도 매우 빠름
            search_k = self.index.ntotal

        search_k = min(search_k, self.index.ntotal)  # 전체 벡터 수 초과 방지

        # FAISS 검색
        scores, indices = self.index.search(query_vector, search_k)

        # 결과 구성
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:  # FAISS에서 결과 없음
                continue

            idx = int(idx)

            # 필터링 적용
            if allowed_indices is not None and idx not in allowed_indices:
                continue

            result = {
                "score": float(score),
                "index": idx,
            }
            results.append(result)

            # 충분한 결과 수집
            if len(results) >= k:
                break

        logger.info(f"Search completed: {len(results)} results returned (requested k={k}, search_k={search_k})")
        return results

    def _preprocess_query(self, query_vector: np.ndarray) -> np.ndarray:
        """쿼리 벡터 전처리"""
        # shape 확인 및 변환
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        # float32로 변환
        query_vector = query_vector.astype("float32")

        # L2 정규화 (Cosine similarity를 위해)
        distance_metric = self.config["vector"]["distance_metric"]
        if distance_metric == "cosine":
            faiss.normalize_L2(query_vector)

        return query_vector

    @property
    def index_path(self) -> Path:
        """인덱스 파일 경로"""
        return get_index_path(self.config)

    @property
    def embeddings_path(self) -> Path:
        """임베딩 파일 경로"""
        return get_embeddings_path(self.config)

    @property
    def total_vectors(self) -> int:
        """전체 벡터 수"""
        if not self._loaded:
            return 0
        return self.index.ntotal if self.index else 0

    def __repr__(self) -> str:
        return f"FAISSManager(loaded={self._loaded}, vectors={self.total_vectors})"
