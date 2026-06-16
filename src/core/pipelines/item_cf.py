"""
아이템 기반 협업 필터링 파이프라인 (코사인 유사도).
기준 영화와 유사한 영화를 찾습니다.
"""

import logging

import pandas as pd

from core.db.data_access import load_movie_data
from core.modeling.models.item_based.model import ItemBasedModel

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
            result = _apply_filters(result, filters)

        return (
            result.sort_values("similarity", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )


def _apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    if "genre" in filters and filters["genre"]:
        genre_list = filters["genre"]
        if isinstance(genre_list, str):
            genre_list = [genre_list]
        if "genres_tmdb" in df.columns:
            mask = df["genres_tmdb"].apply(
                lambda x: any(g in str(x) for g in genre_list) if pd.notna(x) else False
            )
            df = df[mask]

    if "min_year" in filters and filters["min_year"] is not None:
        if "year" in df.columns:
            df = df[df["year"] >= filters["min_year"]]

    if "max_year" in filters and filters["max_year"] is not None:
        if "year" in df.columns:
            df = df[df["year"] <= filters["max_year"]]

    if "language" in filters and filters["language"]:
        lang_list = filters["language"]
        if isinstance(lang_list, str):
            lang_list = [lang_list]
        if "language" in df.columns:
            mask = df["language"].apply(
                lambda x: any(lang in str(x) for lang in lang_list) if pd.notna(x) else False
            )
            df = df[mask]

    return df
