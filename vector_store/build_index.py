"""
FAISS Index Builder

서버(GPU)에서 실행하여 영화 포스터 임베딩을 생성하고 FAISS 인덱스를 구축하는 스크립트

Usage:
    python -m vector_store.build_index --data_path /path/to/movies.csv --output_dir ./indices
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import numpy as np

try:
    import faiss
except ImportError:
    raise ImportError("FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu")

from .config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexBuilder:
    """FAISS 인덱스 빌더"""
    
    def __init__(
        self,
        vector_dim: int = 512,
        distance_metric: str = "cosine"
    ):
        """
        Args:
            vector_dim: 벡터 차원 (CLIP: 512)
            distance_metric: 거리 메트릭 (cosine, l2, ip)
        """
        self.vector_dim = vector_dim
        self.distance_metric = distance_metric
        self.embeddings: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
    
    def add_item(
        self,
        embedding: np.ndarray,
        movie_id: int,
        title: str,
        genres: List[str],
        year: int,
        poster_url: str = "",
        **kwargs
    ) -> None:
        """
        아이템 추가
        
        Args:
            embedding: 이미지 임베딩 벡터
            movie_id: 영화 ID
            title: 영화 제목
            genres: 장르 리스트
            year: 개봉 연도
            poster_url: 포스터 URL
            **kwargs: 추가 메타데이터
        """
        self.embeddings.append(embedding)
        
        metadata = {
            "movie_id": movie_id,
            "title": title,
            "genres": genres,
            "year": year,
            "poster_url": poster_url,
            **kwargs
        }
        self.metadata.append(metadata)
    
    def build(self) -> faiss.Index:
        """FAISS 인덱스 빌드"""
        if not self.embeddings:
            raise ValueError("No embeddings to build index")
        
        logger.info(f"Building FAISS index with {len(self.embeddings)} vectors")
        
        # NumPy 배열로 변환
        embeddings_array = np.vstack(self.embeddings).astype('float32')
        logger.info(f"Embeddings shape: {embeddings_array.shape}")
        
        # L2 정규화 (Cosine similarity를 위해)
        if self.distance_metric == "cosine":
            logger.info("Normalizing vectors for cosine similarity")
            faiss.normalize_L2(embeddings_array)
        
        # FAISS 인덱스 생성
        if self.distance_metric == "cosine":
            # Inner Product (정규화 후 = Cosine similarity)
            index = faiss.IndexFlatIP(self.vector_dim)
        elif self.distance_metric == "l2":
            index = faiss.IndexFlatL2(self.vector_dim)
        else:
            raise ValueError(f"Unsupported distance metric: {self.distance_metric}")
        
        # 벡터 추가
        logger.info("Adding vectors to index...")
        index.add(embeddings_array)
        logger.info(f"Index built: {index.ntotal} vectors")
        
        return index
    
    def save(
        self,
        output_dir: Path,
        index_name: str = "movie_posters",
        save_embeddings: bool = True
    ) -> None:
        """
        인덱스와 메타데이터 저장
        
        Args:
            output_dir: 출력 디렉토리
            index_name: 인덱스 파일명 (확장자 제외)
            save_embeddings: 임베딩 원본도 저장할지 여부 (백업용)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 타임스탬프 추가 (버전 관리)
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # 인덱스 빌드
        index = self.build()
        
        # 인덱스 저장
        index_path = output_dir / f"{index_name}.index"
        logger.info(f"Saving index to {index_path}")
        faiss.write_index(index, str(index_path))
        
        # 버전별 인덱스도 저장
        versioned_index_path = output_dir / f"{index_name}_{timestamp}.index"
        faiss.write_index(index, str(versioned_index_path))
        logger.info(f"Versioned index saved to {versioned_index_path}")
        
        # 메타데이터 저장
        metadata_path = output_dir / f"metadata.json"
        logger.info(f"Saving metadata to {metadata_path}")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        
        # 버전별 메타데이터도 저장
        versioned_metadata_path = output_dir / f"metadata_{timestamp}.json"
        with open(versioned_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Versioned metadata saved to {versioned_metadata_path}")
        
        # 임베딩 원본 저장 (선택)
        if save_embeddings:
            embeddings_array = np.vstack(self.embeddings).astype('float32')
            embeddings_path = output_dir / f"embeddings.npy"
            logger.info(f"Saving embeddings to {embeddings_path}")
            np.save(embeddings_path, embeddings_array)
            
            versioned_embeddings_path = output_dir / f"embeddings_{timestamp}.npy"
            np.save(versioned_embeddings_path, embeddings_array)
            logger.info(f"Versioned embeddings saved to {versioned_embeddings_path}")
        
        # 통계 저장
        stats = {
            "total_vectors": len(self.embeddings),
            "vector_dim": self.vector_dim,
            "distance_metric": self.distance_metric,
            "build_date": datetime.now().isoformat(),
            "index_size_mb": index_path.stat().st_size / (1024 * 1024),
            "metadata_size_mb": metadata_path.stat().st_size / (1024 * 1024),
        }
        
        stats_path = output_dir / "build_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Build statistics saved to {stats_path}")
        
        logger.info("=" * 60)
        logger.info("Build completed successfully!")
        logger.info(f"Total vectors: {stats['total_vectors']}")
        logger.info(f"Index size: {stats['index_size_mb']:.2f} MB")
        logger.info(f"Metadata size: {stats['metadata_size_mb']:.2f} MB")
        logger.info("=" * 60)


def main():
    """메인 함수 (예시)"""
    parser = argparse.ArgumentParser(description="Build FAISS index for movie posters")
    parser.add_argument("--config", type=str, default=None,
                        help="Config file path (default: vector_store/config.yaml)")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Output directory (overrides config)")
    
    args = parser.parse_args()
    
    # 설정 로드
    config = load_config(args.config)
    
    # 출력 디렉토리 (명령줄 인자가 우선)
    output_dir = args.output_dir or config['index']['base_dir']
    
    # 빌더 초기화
    builder = IndexBuilder(
        vector_dim=config['vector']['dim'],
        distance_metric=config['vector']['distance_metric']
    )
    
    # TODO: 실제 데이터 로드 및 임베딩 생성
    # 이 부분은 CLIP 모델과 데이터 로더를 사용하여 구현해야 합니다
    logger.warning(
        "This is a template script. "
        "Please implement data loading and embedding generation."
    )
    
    # 예시: 더미 데이터
    logger.info("Creating dummy data for testing...")
    for i in range(100):
        dummy_embedding = np.random.randn(config['vector']['dim']).astype('float32')
        builder.add_item(
            embedding=dummy_embedding,
            movie_id=i,
            title=f"Movie {i}",
            genres=["Action", "Drama"],
            year=2020 + (i % 5),
            poster_url=f"https://example.com/poster_{i}.jpg"
        )
    
    # 인덱스 저장
    builder.save(
        output_dir=Path(output_dir),
        save_embeddings=config['build']['save_embeddings']
    )


if __name__ == "__main__":
    main()

