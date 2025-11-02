"""
Thin wrapper around the persisted recommendation models.
"""
import logging
from pathlib import Path

from modules.core import PROJECT_ROOT, add_project_paths

add_project_paths()

from modeling.models.recommender import MovieRecommender  # noqa: E402

logger = logging.getLogger(__name__)

# 모델 로드 상태 추적 (캐시 확인용)
_service_instance = None


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


def get_recommender_service() -> RecommenderService:
    """
    Get recommender service instance (singleton pattern).
    첫 번째 호출 시에만 모델을 로드하고, 이후 호출은 캐시된 인스턴스를 반환합니다.
    """
    global _service_instance
    
    if _service_instance is None:
        logger.info("📦 RecommenderService 생성 중 (첫 번째 호출)...")
        logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
        models_root = PROJECT_ROOT / "modeling" / "models" / "pkls"
        svd_path = models_root / "trained_svd_pipeline.pkl"
        item_based_path = models_root / "trained_item_based.pkl"
        logger.info(f"모델 경로 확인: SVD={svd_path.exists()}, Item-based={item_based_path.exists()}")
        _service_instance = RecommenderService(svd_path=svd_path, item_based_path=item_based_path)
        logger.debug("✅ RecommenderService 인스턴스 생성 및 캐시 완료")
    else:
        logger.debug("♻️ RecommenderService 캐시에서 반환 (이미 로드됨)")
    
    return _service_instance

