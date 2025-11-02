"""
Thin wrapper around the persisted recommendation models.
"""
import logging
from functools import lru_cache
from pathlib import Path

from modules.core import PROJECT_ROOT, add_project_paths

add_project_paths()

from modeling.models.recommender import MovieRecommender  # noqa: E402

logger = logging.getLogger(__name__)


class RecommenderService:
    """Loads persisted recommender models and exposes helper methods."""

    def __init__(self, svd_path: Path, item_based_path: Path):
        logger.info(f"RecommenderService 초기화 시작")
        logger.info(f"SVD 모델 경로: {svd_path}")
        logger.info(f"Item-based 모델 경로: {item_based_path}")
        
        if not svd_path.exists():
            logger.error(f"SVD pipeline 파일을 찾을 수 없습니다: {svd_path}")
            raise FileNotFoundError(
                f"SVD pipeline not found at {svd_path}. "
                "Run the training pipeline before starting the backend."
            )
        if not item_based_path.exists():
            logger.error(f"Item-based 모델 파일을 찾을 수 없습니다: {item_based_path}")
            raise FileNotFoundError(
                f"Item-based model not found at {item_based_path}. "
                "Run the training pipeline before starting the backend."
            )

        logger.info("모델 파일 확인 완료, MovieRecommender 초기화 중...")
        self._recommender = MovieRecommender(
            svd_pipeline_path=str(svd_path),
            item_based_path=str(item_based_path),
        )
        logger.info("✅ RecommenderService 초기화 완료")

    @property
    def model(self) -> MovieRecommender:
        return self._recommender

    def recommend_for_user(self, *args, **kwargs):
        return self._recommender.recommend_for_user(*args, **kwargs)

    def user_top_watched(self, *args, **kwargs):
        return self._recommender.get_user_top_watched(*args, **kwargs)

    def similar_movies(self, *args, **kwargs):
        return self._recommender.find_similar_movies(*args, **kwargs)


@lru_cache(maxsize=1)
def get_recommender_service() -> RecommenderService:
    """Instantiate the recommender service once per process."""
    logger.info("get_recommender_service 호출됨")
    logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
    models_root = PROJECT_ROOT / "modeling" / "models" / "pkls"
    svd_path = models_root / "trained_svd_pipeline.pkl"
    item_based_path = models_root / "trained_item_based.pkl"
    logger.info(f"모델 경로 확인: SVD={svd_path.exists()}, Item-based={item_based_path.exists()}")
    return RecommenderService(svd_path=svd_path, item_based_path=item_based_path)

