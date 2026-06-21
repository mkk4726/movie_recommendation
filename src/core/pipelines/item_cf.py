"""
아이템 기반 협업 필터링 파이프라인 (코사인 유사도).
기준 영화와 유사한 영화를 찾습니다.
"""

import logging

import pandas as pd

from core.db.data_access import load_movie_data
from core.modeling.models.item_based.model import ItemBasedModel
from core.modeling.utils.filters import apply_movie_filters

logger = logging.getLogger(__name__)

_OVERSAMPLE_FACTOR = 60


class ItemCFPipeline:
    """아이템 유사도 기반 추천 파이프라인."""

    def __init__(self):
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        logger.info("ItemCFPipeline: Item-based 모델 로딩 중...")
        self._model = ItemBasedModel.load()
        logger.info("ItemCFPipeline: Item-based 모델 로딩 완료")

    def search(
        self,
        movie_id: str,
        top_n: int = 10,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        """
        기준 영화와 유사한 영화를 찾습니다.

        Args:
            movie_id: 기준 영화 ID
            top_n: 반환할 영화 수
            filters: 선택 필터 {'genre', 'language', 'min_year', 'max_year'}

        Returns:
            영화 메타데이터 + 'similarity' 컬럼을 포함한 DataFrame
        """
        self._ensure_loaded()
        df_movies = load_movie_data()

        fetch_n = top_n * _OVERSAMPLE_FACTOR if filters else top_n
        similar_df = self._model.predict(movie_id=movie_id, top_n=fetch_n, return_scores=True)

        if similar_df is None or similar_df.empty:
            return pd.DataFrame()

        result = df_movies.merge(
            similar_df[["movie_id", "similarity_score"]], on="movie_id", how="inner"
        )
        result = result.rename(columns={"similarity_score": "similarity"})

        if filters:
            result = apply_movie_filters(
                result,
                genre=filters.get("genre"),
                language=filters.get("language"),
                min_year=filters.get("min_year"),
                max_year=filters.get("max_year"),
            )

        return (
            result.sort_values("similarity", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
