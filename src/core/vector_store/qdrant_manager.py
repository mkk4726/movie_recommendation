"""
Qdrant Manager

Qdrant 벡터 데이터베이스 연결 및 유사도 검색.
FAISSManager와 동일한 검색 인터페이스를 제공합니다.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from .utils.config import load_config

logger = logging.getLogger(__name__)


class QdrantManager:
    """Qdrant 벡터 인덱스 관리 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 벡터 저장소 설정. None이면 기본 설정 사용
        """
        self.config = config or load_config()
        self.client = None
        self._loaded = False

        qdrant_cfg = self.config.get("qdrant", {})
        # 환경변수 우선 (Docker Compose에서 QDRANT_HOST=qdrant 로 주입)
        self.host = os.environ.get("QDRANT_HOST") or qdrant_cfg.get("host", "localhost")
        self.port = int(os.environ.get("QDRANT_PORT") or qdrant_cfg.get("port", 6333))
        self.collection_name = qdrant_cfg.get("collection", "movie_posters")
        self.vector_dim = self.config["vector"]["dim"]
        self.distance_metric = self.config["vector"]["distance_metric"]

    def load(self) -> None:
        """Qdrant에 연결하고 컬렉션 존재를 확인합니다."""
        if self._loaded:
            return

        self._connect()

        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            raise RuntimeError(
                f"컬렉션 '{self.collection_name}'이 없습니다. "
                "rebuild_qdrant_index.py를 먼저 실행하세요:\n"
                "  PYTHONPATH=src python -m core.vector_store.rebuild_qdrant_index"
            )

        count = self.client.count(self.collection_name).count
        logger.info(f"Qdrant 연결 완료: '{self.collection_name}' {count:,}개 벡터")
        self._loaded = True

    def ensure_collection(self) -> None:
        """컬렉션이 없으면 생성합니다 (마이그레이션 스크립트 전용)."""
        from qdrant_client.models import Distance, VectorParams

        if self.client is None:
            self._connect()

        _distance_map = {
            "cosine": Distance.COSINE,
            "l2": Distance.EUCLID,
            "ip": Distance.DOT,
        }
        distance = _distance_map.get(self.distance_metric, Distance.COSINE)

        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_dim, distance=distance),
            )
            logger.info(f"컬렉션 생성: '{self.collection_name}' (dim={self.vector_dim}, distance={distance.name})")
        else:
            logger.info(f"컬렉션 이미 존재: '{self.collection_name}'")

        self._loaded = True

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filter_movie_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색

        Args:
            query_vector: 쿼리 벡터 (shape: (dim,))
            k: 반환할 결과 수
            filter_movie_ids: 검색 대상 movie_id 리스트 (None이면 전체 검색)

        Returns:
            [{"movie_id": str, "score": float}, ...]
        """
        if not self._loaded:
            self.load()

        query_vector = query_vector.flatten().astype("float32")

        query_filter = None
        if filter_movie_ids:
            from qdrant_client.models import FieldCondition, Filter, MatchAny

            int_ids = [int(mid) for mid in filter_movie_ids if str(mid).lstrip("-").isdigit()]
            query_filter = Filter(
                must=[FieldCondition(key="movie_id", match=MatchAny(any=int_ids))]
            )

        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=k,
            query_filter=query_filter,
            with_payload=True,
        ).points

        return [{"movie_id": str(hit.payload["movie_id"]), "score": float(hit.score)} for hit in hits]

    def upsert(
        self,
        embeddings: np.ndarray,
        movie_ids: List[int],
        batch_size: int = 256,
    ) -> None:
        """
        벡터를 배치로 upsert합니다.

        Args:
            embeddings: 임베딩 배열 (shape: [N, dim])
            movie_ids: 영화 ID 리스트 (Qdrant point ID로도 사용)
            batch_size: 배치 크기
        """
        if self.client is None:
            self._connect()

        from qdrant_client.models import PointStruct

        embeddings = embeddings.astype("float32")
        total = len(movie_ids)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            points = [
                PointStruct(
                    id=int(mid),
                    vector=emb.tolist(),
                    payload={"movie_id": int(mid)},
                )
                for emb, mid in zip(embeddings[start:end], movie_ids[start:end])
            ]
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)
            logger.info(f"Upsert: {end}/{total}")

    def _connect(self) -> None:
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError("qdrant-client가 필요합니다: uv add qdrant-client")

        self.client = QdrantClient(host=self.host, port=self.port)
        logger.info(f"Qdrant 연결: {self.host}:{self.port}")

    @property
    def total_vectors(self) -> int:
        if not self._loaded or self.client is None:
            return 0
        return self.client.count(self.collection_name).count

    def __repr__(self) -> str:
        return f"QdrantManager(collection={self.collection_name}, loaded={self._loaded}, vectors={self.total_vectors})"
