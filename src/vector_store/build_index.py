"""
FAISS Index Builder

서버(GPU)에서 실행하여 영화 포스터 임베딩을 생성하고 FAISS 인덱스를 구축하는 스크립트

Usage:
    python -m vector_store.build_index --data_path /path/to/movies.csv --output_dir ./indices
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import faiss
import numpy as np

from .utils.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IndexBuilder:
    """FAISS 인덱스 빌더"""

    def __init__(self, vector_dim: int = 512, distance_metric: str = "cosine"):
        """
        Args:
            vector_dim: 벡터 차원 (CLIP: 512)
            distance_metric: 거리 메트릭 (cosine, l2, ip)
        """
        self.vector_dim = vector_dim
        self.distance_metric = distance_metric
        self.embeddings: List[np.ndarray] = []
        self.movie_ids: List[int] = []

    def add_item(self, embedding: np.ndarray, movie_id: int, **kwargs) -> None:
        """
        아이템 추가

        Args:
            embedding: 이미지 임베딩 벡터
            movie_id: 영화 ID
            **kwargs: 호환성용 (무시됨)
        """
        if movie_id is None:
            raise ValueError("movie_id is required when adding an item")

        self.embeddings.append(embedding)
        self.movie_ids.append(int(movie_id))

    def build(self) -> faiss.Index:
        """FAISS 인덱스 빌드"""
        if not self.embeddings:
            raise ValueError("No embeddings to build index")

        logger.info(f"Building FAISS index with {len(self.embeddings)} vectors")

        try:
            # NumPy 배열로 변환
            logger.info("Converting embeddings to numpy array...")
            embeddings_array = np.vstack(self.embeddings).astype("float32")
            logger.info(f"Embeddings shape: {embeddings_array.shape}")

            # L2 정규화 (Cosine similarity를 위해)
            if self.distance_metric == "cosine":
                logger.info("Normalizing vectors for cosine similarity...")
                faiss.normalize_L2(embeddings_array)
                logger.info("Normalization completed")

            # FAISS 인덱스 생성
            logger.info(f"Creating FAISS index with metric: {self.distance_metric}")
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
        except Exception as e:
            logger.error(f"Error building index: {e}", exc_info=True)
            raise

    def save(self, output_dir: Path, index_name: str = "movie_posters", save_embeddings: bool = True) -> None:
        """
        인덱스 및 부가 파일 저장

        Args:
            output_dir: 출력 디렉토리
            index_name: 인덱스 파일명 (확장자 제외)
            save_embeddings: 임베딩 원본도 저장할지 여부 (백업용)
        """
        output_dir = Path(output_dir)
        # 상대 경로인 경우 절대 경로로 변환
        if not output_dir.is_absolute():
            # 현재 작업 디렉토리 기준으로 변환
            output_dir = Path.cwd() / output_dir

        logger.info(f"Output directory (absolute): {output_dir.resolve()}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 타임스탬프 추가 (버전 관리)
        timestamp = datetime.now().strftime("%Y%m%d")

        # 인덱스 빌드
        try:
            index = self.build()
        except Exception as e:
            logger.error(f"Failed to build index: {e}", exc_info=True)
            raise

        # 인덱스 저장
        index_path = output_dir / f"{index_name}.index"
        logger.info(f"Saving index to {index_path}")
        try:
            faiss.write_index(index, str(index_path))
            logger.info(f"Index saved successfully: {index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}", exc_info=True)
            raise

        # 버전별 인덱스도 저장
        versioned_index_path = output_dir / f"{index_name}_{timestamp}.index"
        faiss.write_index(index, str(versioned_index_path))
        logger.info(f"Versioned index saved to {versioned_index_path}")

        # 임베딩 원본 저장 (선택)
        if save_embeddings:
            embeddings_array = np.vstack(self.embeddings).astype("float32")
            embeddings_path = output_dir / "embeddings.npy"
            logger.info(f"Saving embeddings to {embeddings_path}")
            np.save(embeddings_path, embeddings_array)

            versioned_embeddings_path = output_dir / f"embeddings_{timestamp}.npy"
            np.save(versioned_embeddings_path, embeddings_array)
            logger.info(f"Versioned embeddings saved to {versioned_embeddings_path}")

        # movie_id 저장
        if self.movie_ids:
            movie_ids_path = output_dir / "movie_ids.json"
            logger.info(f"Saving movie IDs to {movie_ids_path}")
            with open(movie_ids_path, "w", encoding="utf-8") as f:
                json.dump(self.movie_ids, f, ensure_ascii=False, indent=2)

            versioned_movie_ids_path = output_dir / f"movie_ids_{timestamp}.json"
            with open(versioned_movie_ids_path, "w", encoding="utf-8") as f:
                json.dump(self.movie_ids, f, ensure_ascii=False, indent=2)
            logger.info(f"Versioned movie IDs saved to {versioned_movie_ids_path}")

        # 통계 저장
        stats = {
            "total_vectors": len(self.embeddings),
            "vector_dim": self.vector_dim,
            "distance_metric": self.distance_metric,
            "build_date": datetime.now().isoformat(),
            "index_size_mb": index_path.stat().st_size / (1024 * 1024),
            "movie_ids_saved": len(self.movie_ids),
        }

        stats_path = output_dir / "build_stats.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Build statistics saved to {stats_path}")

        logger.info("=" * 60)
        logger.info("Build completed successfully!")
        logger.info(f"Total vectors: {stats['total_vectors']}")
        logger.info(f"Index size: {stats['index_size_mb']:.2f} MB")
        logger.info("=" * 60)


def main():
    """메인 함수 (예시)"""
    parser = argparse.ArgumentParser(description="Build FAISS index for movie posters")
    parser.add_argument("--config", type=str, default=None, help="Config file path (default: vector_store/config.yaml)")
    parser.add_argument("--output_dir", type=str, default=None, help="Output directory (overrides config)")

    args = parser.parse_args()

    # 설정 로드
    config = load_config(args.config)

    # 출력 디렉토리 (명령줄 인자가 우선)
    output_dir = args.output_dir or config["index"]["base_dir"]

    # 빌더 초기화
    builder = IndexBuilder(vector_dim=config["vector"]["dim"], distance_metric=config["vector"]["distance_metric"])

    # TODO: 실제 데이터 로드 및 임베딩 생성
    # 이 부분은 CLIP 모델과 데이터 로더를 사용하여 구현해야 합니다
    logger.warning("This is a template script. Please implement data loading and embedding generation.")

    # 예시: 더미 데이터
    logger.info("Creating dummy data for testing...")
    for i in range(100):
        dummy_embedding = np.random.randn(config["vector"]["dim"]).astype("float32")
        builder.add_item(
            embedding=dummy_embedding,
            movie_id=i,
        )

    # 인덱스 저장
    builder.save(output_dir=Path(output_dir), save_embeddings=config["build"]["save_embeddings"])


if __name__ == "__main__":
    main()
