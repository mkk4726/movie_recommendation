"""
사용자 기반 협업 필터링 파이프라인 (SVD).
특정 사용자에게 미감상 영화를 예측 평점 순으로 추천합니다.
"""

import logging

import pandas as pd

from core.db.data_access import load_movie_data
from core.modeling.models.svd.model import SVDModel

logger = logging.getLogger(__name__)


class UserCFPipeline:
    """SVD 기반 사용자 맞춤 추천 파이프라인."""

    def __init__(self):
        self._svd = None
        self._df_trainset: pd.DataFrame | None = None

    def _ensure_loaded(self):
        if self._svd is not None:
            return
        logger.info("UserCFPipeline: SVD 모델 로딩 중...")
        self._svd = SVDModel.load_model(use_total_data=True)
        trainset = self._svd.trainset
        self._df_trainset = pd.DataFrame(
            [
                {"user_id": trainset.to_raw_uid(u), "movie_id": trainset.to_raw_iid(i), "rating": r}
                for (u, i, r) in trainset.all_ratings()
            ]
        )
        logger.info("UserCFPipeline: SVD 모델 로딩 완료")

    def user_in_trainset(self, user_id: str) -> bool:
        """해당 사용자가 학습 데이터에 존재하는지 확인합니다."""
        self._ensure_loaded()
        return user_id in self._df_trainset["user_id"].values

    def recommend(self, user_id: str, top_n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        사용자에게 영화를 추천합니다.

        Returns:
            (top_watched_df, recommendations_df)
            - top_watched_df: 사용자가 높게 평가한 영화 (movie metadata + rating 컬럼)
            - recommendations_df: 추천 영화 (movie metadata + predicted_rating 컬럼)
        """
        self._ensure_loaded()
        df_movies = load_movie_data()

        user_watched = self._df_trainset.loc[
            self._df_trainset["user_id"] == user_id, "movie_id"
        ]
        candidate_ids = df_movies.loc[
            ~df_movies["movie_id"].isin(user_watched), "movie_id"
        ]

        predictions = [
            (mid, self._svd.predict(user_id, mid).est)
            for mid in candidate_ids.values
        ]
        top = sorted(predictions, key=lambda x: x[1], reverse=True)[:top_n]

        pred_map = dict(top)
        top_ids = [mid for mid, _ in top]

        recs = df_movies[df_movies["movie_id"].isin(top_ids)].copy()
        recs["predicted_rating"] = recs["movie_id"].map(pred_map)
        recs = recs.sort_values("predicted_rating", ascending=False).reset_index(drop=True)

        top_watched_raw = self._df_trainset.loc[
            self._df_trainset["user_id"] == user_id
        ].nlargest(top_n, "rating")

        if not top_watched_raw.empty:
            top_watched_df = df_movies.merge(
                top_watched_raw[["movie_id", "rating"]], on="movie_id", how="inner"
            ).sort_values("rating", ascending=False)
        else:
            top_watched_df = pd.DataFrame()

        return top_watched_df, recs
