"""
Qdrant 포스터 벡터 재구축 스크립트

포스터 이미지를 CLIP/SigLIP 모델로 임베딩하고 Qdrant에 upsert합니다.
모델을 교체한 뒤에는 반드시 이 스크립트를 실행해야 검색 품질이 유지됩니다.

Usage:
    PYTHONPATH=src python -m core.vector_store.rebuild_qdrant_index
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv

import numpy as np
import requests
import torch
from PIL import Image
from tqdm import tqdm

current_dir = Path(__file__).resolve().parent
src_root = current_dir.parent
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from app.services.data_access import load_movie_data
from core.modeling.models.clip.models.base import BaseClipEncoder
from core.modeling.models.clip.utils import make_square
from core.vector_store.qdrant_manager import QdrantManager
from core.vector_store.utils.config import get_clip_model_key, load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class QdrantIndexRebuilder:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        build_config = self.config.get("build", {})
        self.timeout = build_config.get("timeout", 10)
        self.download_batch_size = build_config.get("download_batch_size", 100)
        self.encoding_batch_size = build_config.get("encoding_batch_size", 32)
        self.max_workers = build_config.get("max_workers", 20)
        self.max_retries = build_config.get("max_retries", 3)

        model_key = get_clip_model_key(self.config)
        logger.info("CLIP 인코더 초기화 중... (model=%s)", model_key)
        self.encoder = BaseClipEncoder(model_key=model_key)
        logger.info("CLIP 인코더 초기화 완료 (device=%s)", self.encoder.device)

        self.qdrant = QdrantManager(config=self.config)
        self.qdrant.ensure_collection()

    def rebuild(self) -> None:
        logger.info("=" * 80)
        logger.info("Qdrant 포스터 벡터 재구축 시작")
        logger.info("=" * 80)

        movie_df = load_movie_data()
        movie_data = movie_df[["movie_id", "poster_path"]].copy()
        movie_data = movie_data[movie_data["poster_path"].notna()].reset_index(drop=True)
        movie_data["poster_url"] = movie_data["poster_path"].apply(
            lambda x: f"https://image.tmdb.org/t/p/w300/{x}"
        )
        logger.info("포스터가 있는 영화: %s개", f"{len(movie_data):,}")

        movie_list = [(int(row["movie_id"]), row["poster_url"]) for _, row in movie_data.iterrows()]
        success_count = 0
        error_count = 0

        with tqdm(total=len(movie_list), desc="전체 진행", unit="영화") as pbar:
            for i in range(0, len(movie_list), self.download_batch_size):
                batch = movie_list[i : i + self.download_batch_size]
                downloaded = self._download_batch(batch)
                error_count += len(batch) - len(downloaded)

                if not downloaded:
                    pbar.update(len(batch))
                    continue

                for j in range(0, len(downloaded), self.encoding_batch_size):
                    enc_batch = downloaded[j : j + self.encoding_batch_size]
                    try:
                        movie_ids = [item[0] for item in enc_batch]
                        images = [item[1] for item in enc_batch]
                        embeddings = self._encode_batch(images).cpu().numpy().astype("float32")
                        self.qdrant.upsert(embeddings=embeddings, movie_ids=movie_ids)
                        success_count += len(movie_ids)
                    except Exception as exc:
                        logger.error("배치 upsert 실패: %s", exc)
                        error_count += len(enc_batch)

                    pbar.update(len(enc_batch))
                    pbar.set_postfix(success=success_count, error=error_count)

        logger.info("처리 완료: 성공 %s개, 실패 %s개", f"{success_count:,}", f"{error_count:,}")
        if success_count == 0:
            raise RuntimeError("임베딩 생성에 실패했습니다.")

        logger.info("=" * 80)
        logger.info("✅ Qdrant 재구축 완료 (총 %s개 벡터)", f"{self.qdrant.total_vectors:,}")
        logger.info("=" * 80)

    def _download_image(self, movie_id: int, poster_url: str) -> Optional[Tuple[int, Image.Image]]:
        for attempt in range(self.max_retries):
            try:
                response = requests.get(poster_url, timeout=self.timeout)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGB")
                return movie_id, image
            except Exception as exc:
                if attempt == self.max_retries - 1:
                    logger.debug("영화 ID %s 다운로드 실패: %s", movie_id, exc)
                    return None
        return None

    def _download_batch(self, batch_data: List[Tuple[int, str]]) -> List[Tuple[int, Image.Image]]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._download_image, movie_id, url)
                for movie_id, url in batch_data
            ]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
        return results

    def _encode_batch(self, images: List[Image.Image]) -> torch.Tensor:
        processed_images = [make_square(img) for img in images]
        inputs = self.encoder.processor(images=processed_images, return_tensors="pt").to(self.encoder.device)
        with torch.no_grad():
            embeddings = self.encoder.model.get_image_features(**inputs)
        return embeddings / embeddings.norm(dim=-1, keepdim=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    try:
        rebuilder = QdrantIndexRebuilder(config=load_config())
        rebuilder.rebuild()
    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as exc:
        logger.error("오류 발생: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
