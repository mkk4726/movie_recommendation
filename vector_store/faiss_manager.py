"""
FAISS Manager

FAISS 인덱스를 관리하고 유사도 검색을 수행하는 클래스
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError(
        "FAISS is not installed. Please install it with: pip install faiss-cpu"
    )

from .config import VectorStoreConfig

logger = logging.getLogger(__name__)


class FAISSManager:
    """FAISS 벡터 인덱스 관리 클래스"""
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Args:
            config: 벡터 저장소 설정. None이면 기본 설정 사용
        """
        self.config = config or VectorStoreConfig.default()
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._loaded = False
        
        logger.info(f"FAISSManager initialized with config: {self.config}")
    
    def load(self) -> None:
        """인덱스와 메타데이터 로드"""
        if self._loaded:
            logger.warning("Index already loaded")
            return
        
        # 인덱스 로드
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Index file not found: {self.index_path}\n"
                "Please build the index first using build_index.py"
            )
        
        logger.info(f"Loading FAISS index from {self.index_path}")
        self.index = faiss.read_index(str(self.index_path))
        logger.info(f"Index loaded: {self.index.ntotal} vectors")
        
        # 메타데이터 로드
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {self.metadata_path}"
            )
        
        logger.info(f"Loading metadata from {self.metadata_path}")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        # 리스트를 딕셔너리로 변환 (인덱스로 접근)
        if isinstance(metadata_list, list):
            self.metadata = {i: meta for i, meta in enumerate(metadata_list)}
        else:
            self.metadata = {int(k): v for k, v in metadata_list.items()}
        
        logger.info(f"Metadata loaded: {len(self.metadata)} entries")
        self._loaded = True
    
    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색 수행
        
        Args:
            query_vector: 쿼리 벡터 (shape: (512,) or (1, 512))
            k: 반환할 결과 수
            filters: 메타데이터 필터
                - genres: List[str] - 장르 필터 (OR 조건)
                - year_min: int - 최소 연도
                - year_max: int - 최대 연도
                - rating_min: float - 최소 평점
        
        Returns:
            검색 결과 리스트 (score 내림차순)
        """
        if not self._loaded:
            self.load()
        
        # 벡터 전처리
        query_vector = self._preprocess_query(query_vector)
        
        # 필터링이 있으면 더 많이 검색
        search_multiplier = self.config['search']['search_multiplier']
        search_k = k * search_multiplier if filters else k
        search_k = min(search_k, self.index.ntotal)  # 전체 벡터 수 초과 방지
        
        # FAISS 검색
        scores, indices = self.index.search(query_vector, search_k)
        
        # 결과 구성
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:  # FAISS에서 결과 없음
                continue
            
            idx = int(idx)
            if idx not in self.metadata:
                logger.warning(f"Metadata not found for index {idx}")
                continue
            
            meta = self.metadata[idx]
            
            # 필터 적용
            if filters and not self._apply_filters(meta, filters):
                continue
            
            result = {
                "score": float(score),
                "index": idx,
                **meta
            }
            results.append(result)
            
            # 충분한 결과 수집
            if len(results) >= k:
                break
        
        logger.info(f"Search completed: {len(results)} results returned")
        return results
    
    def search_by_id(
        self,
        movie_id: Union[int, str],
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        영화 ID로 유사한 영화 검색
        
        Args:
            movie_id: 영화 ID
            k: 반환할 결과 수 (자기 자신 제외)
            filters: 메타데이터 필터
        
        Returns:
            검색 결과 리스트
        """
        if not self._loaded:
            self.load()
        
        # 영화 ID로 인덱스 찾기
        idx = self._find_index_by_movie_id(movie_id)
        if idx is None:
            logger.warning(f"Movie ID {movie_id} not found")
            return []
        
        # 해당 벡터 가져오기
        vector = self.index.reconstruct(idx)
        
        # 검색 (k+1개 검색 후 자기 자신 제거)
        results = self.search(vector, k=k+1, filters=filters)
        
        # 자기 자신 제거
        results = [r for r in results if r.get("movie_id") != movie_id][:k]
        
        return results
    
    def get_metadata(self, idx: int) -> Optional[Dict[str, Any]]:
        """인덱스로 메타데이터 조회"""
        if not self._loaded:
            self.load()
        return self.metadata.get(idx)
    
    def get_metadata_by_movie_id(self, movie_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """영화 ID로 메타데이터 조회"""
        if not self._loaded:
            self.load()
        
        for meta in self.metadata.values():
            if str(meta.get("movie_id")) == str(movie_id):
                return meta
        return None
    
    def _preprocess_query(self, query_vector: np.ndarray) -> np.ndarray:
        """쿼리 벡터 전처리"""
        # shape 확인 및 변환
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # float32로 변환
        query_vector = query_vector.astype('float32')
        
        # L2 정규화 (Cosine similarity를 위해)
        distance_metric = self.config['vector']['distance_metric']
        if distance_metric == "cosine":
            faiss.normalize_L2(query_vector)
        
        return query_vector
    
    def _apply_filters(self, meta: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """메타데이터 필터 적용"""
        # 장르 필터 (OR 조건)
        if "genres" in filters:
            filter_genres = filters["genres"]
            if isinstance(filter_genres, str):
                filter_genres = [filter_genres]
            
            meta_genres = meta.get("genres", [])
            if isinstance(meta_genres, str):
                meta_genres = [meta_genres]
            
            if not any(g in meta_genres for g in filter_genres):
                return False
        
        # 연도 필터
        if "year_min" in filters:
            year = meta.get("year")
            if year is None or year < filters["year_min"]:
                return False
        
        if "year_max" in filters:
            year = meta.get("year")
            if year is None or year > filters["year_max"]:
                return False
        
        # 평점 필터
        if "rating_min" in filters:
            rating = meta.get("rating")
            if rating is None or rating < filters["rating_min"]:
                return False
        
        return True
    
    def _find_index_by_movie_id(self, movie_id: Union[int, str]) -> Optional[int]:
        """영화 ID로 인덱스 찾기"""
        movie_id_str = str(movie_id)
        for idx, meta in self.metadata.items():
            if str(meta.get("movie_id")) == movie_id_str:
                return idx
        return None
    
    @property
    def total_vectors(self) -> int:
        """전체 벡터 수"""
        if not self._loaded:
            return 0
        return self.index.ntotal if self.index else 0
    
    def __repr__(self) -> str:
        return (
            f"FAISSManager("
            f"loaded={self._loaded}, "
            f"vectors={self.total_vectors}, "
            f"metadata={len(self.metadata)})"
        )

