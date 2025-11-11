"""
영화 검색에 특화된 BM25 모듈

여러 필드(제목, 장르, 태그 등)에 대해 가중치를 적용한 검색을 지원합니다.
"""
import logging
import pickle
from pathlib import Path
from typing import List, Optional
from collections import defaultdict

from .config import BM25Config
from .core import BM25
from .models import BM25SearchResult

logger = logging.getLogger(__name__)


class MovieBM25:
    """
    영화 검색에 특화된 BM25 래퍼 클래스
    여러 필드(제목, 장르, 태그 등)에 대해 가중치를 적용한 검색을 지원합니다.
    """
    
    def __init__(self, config: Optional[BM25Config] = None, yaml_path: Optional[str] = None):
        """
        MovieBM25 초기화
        
        Args:
            config: BM25Config 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
        """
        # 설정 로드
        if config is None:
            self.config = BM25Config.from_yaml(yaml_path)
        else:
            self.config = config
        
        # 각 필드별 BM25 인스턴스 생성
        self.bm25_instances = {}
        for field in self.config.field_weights.keys():
            self.bm25_instances[field] = BM25(config=self.config)
        
        logger.info(f"✅ MovieBM25 초기화 완료 (필드: {list(self.config.field_weights.keys())})")
    
    def fit(self, movies_df):
        """
        영화 데이터프레임으로 색인 생성
        
        Args:
            movies_df: 영화 데이터프레임 (movie_id, title, genres 등 포함)
        """
        logger.info(f"🔄 영화 데이터 색인 생성 중... ({len(movies_df)}개 영화)")
        
        # 문서 ID 및 메타데이터 준비
        # movie_id 또는 movieId 컬럼 지원
        id_col = 'movie_id' if 'movie_id' in movies_df.columns else 'movieId'
        doc_ids = movies_df[id_col].tolist()
        metadata = []
        
        for _, row in movies_df.iterrows():
            # total_title이 있으면 사용, 없으면 title 사용
            title_value = row.get('total_title', '') or row.get('title', '')
            meta = {
                'title': title_value,
                'genres': row.get('genres', ''),
                'overview': row.get('overview', '')
            }
            metadata.append(meta)
        
        # 각 필드별로 색인 생성
        for field, bm25 in self.bm25_instances.items():
            # title 필드는 total_title을 우선 사용
            actual_field = field
            if field == 'title':
                if 'total_title' in movies_df.columns:
                    actual_field = 'total_title'
                elif 'title' not in movies_df.columns:
                    logger.warning(f"  ⚠️ 'title' 또는 'total_title' 필드가 데이터프레임에 없습니다.")
                    continue
            
            if actual_field in movies_df.columns:
                corpus = movies_df[actual_field].fillna('').astype(str).tolist()
                bm25.fit(corpus, doc_ids, metadata)
                logger.info(f"  ✓ '{field}' 필드 색인 완료 (실제 컬럼: '{actual_field}')")
            else:
                logger.warning(f"  ⚠️ '{field}' 필드가 데이터프레임에 없습니다.")
        
        logger.info("✅ 모든 필드 색인 생성 완료")
    
    def search(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> List[BM25SearchResult]:
        """
        여러 필드를 통합하여 영화 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 개수
            min_score: 최소 스코어 임계값
            
        Returns:
            BM25SearchResult 리스트 (통합 스코어 내림차순 정렬)
        """
        top_k = top_k if top_k is not None else self.config.top_k
        min_score = min_score if min_score is not None else self.config.min_score
        
        logger.info(f"🔍 영화 검색 중: '{query}'")
        
        # 각 필드별 검색 결과를 통합
        combined_scores = defaultdict(lambda: {'score': 0.0, 'fields': {}, 'metadata': {}})
        
        for field, bm25 in self.bm25_instances.items():
            weight = self.config.field_weights.get(field, 1.0)
            results = bm25.search(query, top_k=top_k * 3, min_score=0.0)  # 더 많이 가져와서 통합
            
            for result in results:
                movie_id = result.movie_id
                weighted_score = result.score * weight
                
                combined_scores[movie_id]['score'] += weighted_score
                combined_scores[movie_id]['fields'][field] = weighted_score
                combined_scores[movie_id]['metadata'] = {
                    'title': result.title,
                    'genres': result.genres,
                    'overview': result.overview
                }
        
        # 통합 스코어로 정렬
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        # BM25SearchResult 객체로 변환
        final_results = []
        for movie_id, data in sorted_results[:top_k]:
            if data['score'] >= min_score:
                result = BM25SearchResult(
                    movie_id=movie_id,
                    score=data['score'],
                    title=data['metadata']['title'],
                    genres=data['metadata']['genres'],
                    matched_fields=data['fields'],
                    overview=data['metadata'].get('overview', '')
                )
                final_results.append(result)
        
        logger.info(f"✅ 검색 완료: {len(final_results)}개 결과 반환")
        return final_results
    
    def save(self, dirpath: str):
        """
        모든 필드의 BM25 색인을 디렉토리에 저장
        
        Args:
            dirpath: 저장할 디렉토리 경로
        """
        dirpath = Path(dirpath)
        dirpath.mkdir(parents=True, exist_ok=True)
        
        for field, bm25 in self.bm25_instances.items():
            filepath = dirpath / f"bm25_{field}.pkl"
            bm25.save(str(filepath))
        
        # 설정 저장
        config_path = dirpath / "config.pkl"
        with open(config_path, 'wb') as f:
            pickle.dump(self.config, f)
        
        logger.info(f"💾 MovieBM25 색인 저장 완료: {dirpath}")
    
    @classmethod
    def load(cls, dirpath: str) -> 'MovieBM25':
        """
        디렉토리에서 모든 필드의 BM25 색인 로드
        
        Args:
            dirpath: 로드할 디렉토리 경로
            
        Returns:
            MovieBM25 객체
        """
        dirpath = Path(dirpath)
        
        # 설정 로드
        config_path = dirpath / "config.pkl"
        with open(config_path, 'rb') as f:
            config = pickle.load(f)
        
        # MovieBM25 객체 생성
        movie_bm25 = cls(config=config)
        
        # 각 필드별 BM25 로드
        for field in config.field_weights.keys():
            filepath = dirpath / f"bm25_{field}.pkl"
            if filepath.exists():
                movie_bm25.bm25_instances[field] = BM25.load(str(filepath))
            else:
                logger.warning(f"⚠️ '{field}' 필드 색인 파일을 찾을 수 없습니다: {filepath}")
        
        logger.info(f"📂 MovieBM25 색인 로드 완료: {dirpath}")
        return movie_bm25

