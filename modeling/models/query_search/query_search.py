"""
자연어 검색 파이프라인

사용자의 자연어 쿼리를 받아서 영화 검색 결과를 반환합니다.
BM25 기반 lexical search를 사용합니다.
"""
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

from .lexical_search import MovieBM25, BM25Config, BM25SearchResult

# Pydantic 모델 import (순환 참조 방지)
if TYPE_CHECKING:
    from app.api.models import QuerySearchResponse, SearchResultMovie

logger = logging.getLogger(__name__)


class QuerySearchPipeline:
    """
    자연어 검색 파이프라인
    
    사용자의 자연어 쿼리를 받아서 영화 검색 결과를 반환합니다.
    """
    
    def __init__(
        self,
        bm25_config: Optional[BM25Config] = None,
        yaml_path: Optional[str] = None
    ):
        """
        QuerySearchPipeline 초기화
        
        Args:
            bm25_config: BM25 설정 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (bm25_config가 None일 때 사용)
        """
        logger.info("🚀 QuerySearchPipeline 초기화 중...")
        
        # BM25 검색 엔진 초기화
        self.movie_bm25 = MovieBM25(config=bm25_config, yaml_path=yaml_path)
        self._is_fitted = False
        
        logger.info("✅ QuerySearchPipeline 초기화 완료")
    
    def fit(self, movies_df):
        """
        영화 데이터로 검색 인덱스 생성
        
        Args:
            movies_df: 영화 데이터프레임 (movie_id, title, genres, overview 등 포함)
        """
        logger.info(f"🔄 검색 인덱스 생성 중... ({len(movies_df)}개 영화)")
        
        # BM25 색인 생성
        self.movie_bm25.fit(movies_df)
        self._is_fitted = True
        
        logger.info("✅ 검색 인덱스 생성 완료")
    
    def search(
        self,
        query: str,
        top_k: int = 20,
        min_score: float = 0.0
    ) -> List[BM25SearchResult]:
        """
        자연어 쿼리로 영화 검색
        
        Args:
            query: 사용자의 자연어 검색 쿼리
            top_k: 반환할 상위 결과 개수
            min_score: 최소 스코어 임계값
            
        Returns:
            BM25SearchResult 리스트 (스코어 내림차순 정렬)
            
        Raises:
            RuntimeError: fit()이 호출되지 않은 경우
        """
        if not self._is_fitted:
            raise RuntimeError("검색 인덱스가 생성되지 않았습니다. fit()을 먼저 호출하세요.")
        
        logger.info(f"🔍 자연어 검색: '{query}'")
        
        # BM25로 검색
        results = self.movie_bm25.search(
            query=query,
            top_k=top_k,
            min_score=min_score
        )
        
        logger.info(f"✅ 검색 완료: {len(results)}개 결과 반환")
        return results
    
    def search_to_response(
        self,
        query: str,
        top_k: int = 20,
        min_score: float = 0.0
    ) -> 'QuerySearchResponse':
        """
        자연어 쿼리로 영화 검색 (Pydantic 모델로 반환)
        
        Args:
            query: 사용자의 자연어 검색 쿼리
            top_k: 반환할 상위 결과 개수
            min_score: 최소 스코어 임계값
            
        Returns:
            QuerySearchResponse (Pydantic 모델)
        """
        # Lazy import to avoid circular dependency
        from app.api.models import QuerySearchResponse, SearchResultMovie
        
        results = self.search(query, top_k, min_score)
        
        # BM25SearchResult를 SearchResultMovie로 변환
        search_result_movies = [
            SearchResultMovie(
                movie_id=str(result.movie_id),
                title=result.title,
                genres=result.genres,
                score=result.score,
                overview=result.overview,
                matched_fields=result.matched_fields,
                year=result.year
            )
            for result in results
        ]
        
        return QuerySearchResponse(
            query=query,
            total_results=len(search_result_movies),
            results=search_result_movies
        )
    
    def search_to_dict(
        self,
        query: str,
        top_k: int = 20,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        자연어 쿼리로 영화 검색 (딕셔너리 형태로 반환)
        
        Args:
            query: 사용자의 자연어 검색 쿼리
            top_k: 반환할 상위 결과 개수
            min_score: 최소 스코어 임계값
            
        Returns:
            검색 결과 딕셔너리
        """
        response = self.search_to_response(query, top_k, min_score)
        return response.model_dump()
    
    def save(self, dirpath: str):
        """
        검색 인덱스를 디렉토리에 저장
        
        Args:
            dirpath: 저장할 디렉토리 경로
        """
        if not self._is_fitted:
            logger.warning("⚠️ 검색 인덱스가 생성되지 않았습니다. 저장할 내용이 없습니다.")
            return
        
        dirpath = Path(dirpath)
        dirpath.mkdir(parents=True, exist_ok=True)
        
        # BM25 인덱스 저장
        self.movie_bm25.save(str(dirpath / "bm25"))
        
        logger.info(f"💾 검색 인덱스 저장 완료: {dirpath}")
    
    @classmethod
    def load(cls, dirpath: str) -> 'QuerySearchPipeline':
        """
        디렉토리에서 검색 인덱스 로드
        
        Args:
            dirpath: 로드할 디렉토리 경로
            
        Returns:
            QuerySearchPipeline 객체
        """
        logger.info(f"📂 검색 인덱스 로드 중: {dirpath}")
        
        dirpath = Path(dirpath)
        
        # BM25 인덱스 로드
        movie_bm25 = MovieBM25.load(str(dirpath / "bm25"))
        
        # QuerySearchPipeline 객체 생성
        pipeline = cls.__new__(cls)
        pipeline.movie_bm25 = movie_bm25
        pipeline._is_fitted = True
        
        logger.info("✅ 검색 인덱스 로드 완료")
        return pipeline


# 편의 함수들
def create_search_pipeline(
    movies_df,
    bm25_config: Optional[BM25Config] = None,
    yaml_path: Optional[str] = None
) -> QuerySearchPipeline:
    """
    검색 파이프라인 생성 및 인덱스 생성
    
    Args:
        movies_df: 영화 데이터프레임
        bm25_config: BM25 설정 객체
        yaml_path: YAML 파일 경로
        
    Returns:
        학습된 QuerySearchPipeline 객체
    """
    pipeline = QuerySearchPipeline(bm25_config=bm25_config, yaml_path=yaml_path)
    pipeline.fit(movies_df)
    return pipeline


def search_movies(
    pipeline: QuerySearchPipeline,
    query: str,
    top_k: int = 20,
    min_score: float = 0.0,
    return_type: str = "pydantic"
):
    """
    영화 검색 편의 함수
    
    Args:
        pipeline: QuerySearchPipeline 객체
        query: 검색 쿼리
        top_k: 반환할 상위 결과 개수
        min_score: 최소 스코어 임계값
        return_type: 반환 타입
            - "pydantic": QuerySearchResponse (Pydantic 모델) 반환 (기본값)
            - "dict": 딕셔너리로 반환
            - "raw": BM25SearchResult 리스트로 반환
        
    Returns:
        검색 결과 (return_type에 따라 형태가 다름)
    """
    if return_type == "pydantic":
        return pipeline.search_to_response(query, top_k, min_score)
    elif return_type == "dict":
        return pipeline.search_to_dict(query, top_k, min_score)
    elif return_type == "raw":
        return pipeline.search(query, top_k, min_score)
    else:
        raise ValueError(f"Invalid return_type: {return_type}. Must be 'pydantic', 'dict', or 'raw'.")

