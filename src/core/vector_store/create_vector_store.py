"""
Vector Store 생성 스크립트

영화 포스터 이미지를 CLIP 모델로 임베딩하고 FAISS 인덱스를 생성합니다.

Usage:
    python -m vector_store.create_vector_store

설정은 vector_store/config.yaml에서 수정하세요.
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import requests
import torch
from PIL import Image
from tqdm import tqdm

# 프로젝트 루트를 sys.path에 추가
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 프로젝트 모듈 import (sys.path 설정 후)
from src.data_scraping.common.data_loader import load_movie_data
from src.modeling.models.clip.models.base import BaseClipEncoder
from src.vector_store.build_index import IndexBuilder
from src.vector_store.utils.config import get_clip_model_key, load_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VectorStoreCreator:
    """Vector Store 생성 클래스"""

    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: 설정 딕셔너리 (None이면 기본 설정 사용)
        """
        self.config = config or load_config()

        # 빌드 설정 로드
        build_config = self.config.get("build", {})
        self.timeout = build_config.get("timeout", 10)
        self.download_batch_size = build_config.get("download_batch_size", 100)
        self.encoding_batch_size = build_config.get("encoding_batch_size", 32)
        self.max_workers = build_config.get("max_workers", 20)
        self.max_retries = build_config.get("max_retries", 3)

        # CLIP 인코더 초기화
        model_key = get_clip_model_key(self.config)
        logger.info("CLIP 인코더 초기화 중... (model=%s)", model_key)
        self.encoder = BaseClipEncoder(model_key=model_key)
        logger.info(f"CLIP 인코더 초기화 완료 (device: {self.encoder.device})")

        # 인덱스 빌더 초기화
        self.builder = IndexBuilder(
            vector_dim=self.config["vector"]["dim"],
            distance_metric=self.config["vector"]["distance_metric"],
        )

    def create(self, output_dir: Optional[Path] = None) -> None:
        """
        Vector Store 생성

        Args:
            output_dir: 출력 디렉토리 (None이면 config 사용)
        """
        # 출력 디렉토리 설정 (프로젝트 루트 기준 절대 경로)
        if output_dir is None:
            # 프로젝트 루트 기준으로 vector_store/indices 경로 생성
            base_dir_str = self.config["index"]["base_dir"]
            output_dir = project_root / base_dir_str
        else:
            output_dir = Path(output_dir)
            # 상대 경로인 경우 프로젝트 루트 기준으로 변환
            if not output_dir.is_absolute():
                output_dir = project_root / output_dir

        logger.info("=" * 80)
        logger.info("Vector Store 생성 시작")
        logger.info("=" * 80)

        # 1. 영화 데이터 로드
        logger.info("\n[1/3] 영화 데이터 로딩 중...")
        movie_df = load_movie_data()
        logger.info(f"총 {len(movie_df):,}개 영화 로드 완료")

        # 2. 포스터가 있는 영화만 필터링
        logger.info("\n[2/3] 포스터 데이터 필터링 중...")
        movie_data = movie_df[["movie_id", "poster_path"]].copy()
        movie_data = movie_data[movie_data["poster_path"].notna()].reset_index(drop=True)
        movie_data["poster_url"] = movie_data["poster_path"].apply(lambda x: f"https://image.tmdb.org/t/p/w300/{x}")
        logger.info(f"포스터가 있는 영화: {len(movie_data):,}개")

        # 3. 임베딩 생성 및 인덱스 빌드
        logger.info("\n[3/3] 임베딩 생성 및 인덱스 빌드 중...")
        self._process_embeddings(movie_data)

        # 4. 인덱스 저장
        logger.info(f"인덱스 저장 중: {output_dir}")
        index_name = self.config["index"]["index_file"].replace(".index", "")
        self.builder.save(
            output_dir=output_dir,
            index_name=index_name,
            save_embeddings=self.config["build"]["save_embeddings"],
        )

        logger.info("\n" + "=" * 80)
        logger.info("✅ Vector Store 생성 완료!")
        logger.info("=" * 80)

    def _download_image(self, movie_id: int, poster_url: str) -> Optional[Tuple[int, Image.Image]]:
        """
        단일 이미지 다운로드 (재시도 로직 포함)

        Args:
            movie_id: 영화 ID
            poster_url: 포스터 URL

        Returns:
            (movie_id, PIL Image) 튜플 또는 None (실패 시)
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(poster_url, timeout=self.timeout)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGB")
                return (movie_id, image)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    msg = f"영화 ID {movie_id} 다운로드 실패"
                    msg += f" (재시도 {self.max_retries}회): {e}"
                    logger.debug(msg)
                    return None
        return None

    def _download_batch(self, batch_data: List[Tuple[int, str]]) -> List[Tuple[int, Image.Image]]:
        """
        배치 이미지 다운로드 (멀티스레딩)

        Args:
            batch_data: [(movie_id, poster_url), ...] 리스트

        Returns:
            [(movie_id, PIL Image), ...] 리스트
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 다운로드 작업 제출
            future_to_movie = {
                executor.submit(self._download_image, movie_id, url): movie_id for movie_id, url in batch_data
            }

            # 완료된 작업 수집
            for future in as_completed(future_to_movie):
                result = future.result()
                if result is not None:
                    results.append(result)

        return results

    def _encode_batch(self, images: List[Image.Image]) -> torch.Tensor:
        """
        배치 이미지 인코딩 (GPU 최적화)

        Args:
            images: PIL Image 리스트

        Returns:
            임베딩 텐서 (batch_size, embedding_dim)
        """
        # 이미지 전처리 (정사각형 변환)
        from modeling.models.clip.utils import make_square

        processed_images = [make_square(img) for img in images]

        # 배치 처리
        inputs = self.encoder.processor(images=processed_images, return_tensors="pt").to(self.encoder.device)

        with torch.no_grad():
            embeddings = self.encoder.model.get_image_features(**inputs)

        # 정규화
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        return embeddings

    def _process_embeddings(self, movie_data) -> None:
        """
        영화 포스터 임베딩 생성 및 인덱스에 추가 (배치 + 멀티스레딩)

        Args:
            movie_data: 영화 데이터 (movie_id, poster_url 포함)
        """
        success_count = 0
        error_count = 0
        total_movies = len(movie_data)

        # 데이터를 배치로 분할
        movie_list = []
        for _, row in movie_data.iterrows():
            movie_list.append((row["movie_id"], row["poster_url"]))

        logger.info(f"배치 크기: 다운로드={self.download_batch_size}, 인코딩={self.encoding_batch_size}")
        logger.info(f"다운로드 스레드: {self.max_workers}개")

        # 전체 진행률 표시
        with tqdm(total=total_movies, desc="전체 진행", unit="영화") as pbar:
            # 다운로드 배치 단위로 처리
            for i in range(0, len(movie_list), self.download_batch_size):
                batch = movie_list[i : i + self.download_batch_size]

                # 1단계: 배치 다운로드 (멀티스레딩)
                downloaded = self._download_batch(batch)
                error_count += len(batch) - len(downloaded)

                if not downloaded:
                    pbar.update(len(batch))
                    continue

                # 2단계: 인코딩 배치로 분할 처리
                for j in range(0, len(downloaded), self.encoding_batch_size):
                    enc_batch = downloaded[j : j + self.encoding_batch_size]

                    try:
                        # 영화 ID와 이미지 분리
                        movie_ids = [item[0] for item in enc_batch]
                        images = [item[1] for item in enc_batch]

                        # 배치 인코딩
                        embeddings = self._encode_batch(images)

                        # NumPy 변환 및 인덱스 추가
                        embeddings_np = embeddings.cpu().numpy()
                        embeddings_np = embeddings_np.astype("float32")

                        for movie_id, embedding in zip(movie_ids, embeddings_np):
                            self.builder.add_item(embedding=embedding, movie_id=int(movie_id))
                            success_count += 1

                    except Exception as e:
                        logger.error(f"배치 인코딩 실패: {e}")
                        error_count += len(enc_batch)

                    # 진행률 업데이트
                    pbar.update(len(enc_batch))
                    total = success_count + error_count
                    rate = f"{success_count / total * 100:.1f}%"
                    pbar.set_postfix(
                        {
                            "success": success_count,
                            "error": error_count,
                            "success_rate": rate,
                        }
                    )

        logger.info(f"\n처리 완료: 성공 {success_count:,}개, 실패 {error_count:,}개")
        logger.info(f"성공률: {success_count / total_movies * 100:.2f}%")

        if success_count == 0:
            raise RuntimeError("임베딩 생성에 실패했습니다. 네트워크 연결을 확인하세요.")


def main():
    """메인 함수"""
    try:
        # 설정 로드
        logger.info("설정 파일 로딩 중...")
        config = load_config()

        # 출력 디렉토리 (프로젝트 루트 기준 절대 경로)
        base_dir_str = config["index"]["base_dir"]
        output_dir = project_root / base_dir_str

        # Vector Store 생성
        creator = VectorStoreCreator(config=config)
        creator.create(output_dir=output_dir)

    except KeyboardInterrupt:
        logger.warning("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n\n오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
