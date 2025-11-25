"""
영화 추천 시스템 모듈 - 추천 전략별 모델을 불러와서 사용하는 래퍼 클래스
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from modeling.models.item_based.model import ItemBasedModel
from modeling.models.svd.model import SVDModel

logger = logging.getLogger(__name__)


class MovieRecommender:
    """
    영화 추천 시스템 래퍼 클래스

    추천 전략별로 저장된 모델을 불러와서 사용합니다:
    - CF (Collaborative Filtering): SVDRecommenderPipeline (사용자 맞춤 추천)
    - Item-Based CF: ItemBasedRecommender (영화 간 유사도 기반 추천)
    """

    def __init__(self):
        """
        Args:
            svd_pipeline_path: SVD 파이프라인 pkl 파일 경로
            item_based_path: Item-Based 모델 pkl 파일 경로
        """
        logger.info("=" * 60)
        logger.info("🎬 MovieRecommender 초기화 시작")
        logger.info("=" * 60)

        # CF 모델 - 사용자 맞춤 추천용
        logger.info("SVD 모델 로드 시작")
        self.svd_model = SVDModel.load_model(use_total_data=True)
        trainset = self.svd_model.trainset
        self.df_trainset = pd.DataFrame(
            [
                {"user_id": trainset.to_raw_uid(u), "movie_id": trainset.to_raw_iid(i), "rating": r}
                for (u, i, r) in trainset.all_ratings()
            ]
        )
        logger.info("SVD 모델 로드 완료")

        # Item-based 모델 - 유사한 영화 추천용
        logger.info("Item-based 모델 로드 시작")
        self.item_based_model = ItemBasedModel.load()
        logger.info("Item-based 모델 로드 완료")

        logger.info("=" * 60)
        logger.info("✅ MovieRecommender 초기화 완료")
        logger.info("=" * 60)

    def recommend_for_user(self, user_id: str, df_movies: pd.DataFrame, n_recommendations: int = 10):
        """
        특정 사용자에게 영화 추천 (협업 필터링 - CF 기반)

        Args:
            user_id: 사용자 ID
            df_movies: 영화 정보 데이터프레임
            n_recommendations: 추천할 영화 개수

        Returns:
            (top_watched, recommendations) 튜플
            - top_watched: 사용자가 높게 평가한 영화 DataFrame
            - recommendations: 추천 영화 DataFrame
        """
        if self.svd_model is None:
            raise ValueError("SVD 파이프라인을 먼저 로드해주세요. load_svd_pipeline() 실행 필요")
        user_watched_movies = self.df_trainset.loc[self.df_trainset["user_id"] == user_id, "movie_id"]
        candidate_mask = ~df_movies["movie_id"].isin(user_watched_movies)
        candidate_movie_ids = df_movies.loc[candidate_mask, "movie_id"]

        # candidate_movie_id를 하나씩 넣어서 예측값 뽑아내고 높은 평점으로 정렬하는 코드
        predictions = []
        for movie_id in candidate_movie_ids.values:
            pred = self.svd_model.predict(user_id, movie_id)
            predictions.append((movie_id, pred.est))

        # 예측값으로 정렬
        sorted_predictions = sorted(predictions, key=lambda x: x[1], reverse=True)

        # 상위 10개 추천 영화 ID 추출
        # 상위 n개 추천 영화 ID 추출
        top_movie_ids = [movie_id for movie_id, est in sorted_predictions[:n_recommendations]]

        # 추천 영화 DataFrame 생성
        recommendations = df_movies[df_movies["movie_id"].isin(top_movie_ids)].copy()
        recommendations["pred_rating"] = recommendations["movie_id"].map(dict(sorted_predictions))
        recommendations = recommendations.sort_values("pred_rating", ascending=False)
        recommendations.reset_index(drop=True, inplace=True)

        return recommendations

    def get_user_top_watched(self, user_id: str, df_movies: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        사용자가 높게 평가한 영화 조회

        Args:
            user_id: 사용자 ID
            df_movies: 영화 정보 데이터프레임
            n: 조회할 영화 개수

        Returns:
            높게 평가한 영화 데이터프레임
        """
        if self.svd_pipeline is None:
            raise ValueError("SVD 파이프라인을 먼저 로드해주세요.")

        top_watched = self.df_trainset.loc[self.df_trainset["user_id"] == user_id].nlargest(n, "rating")
        top_watched = df_movies.merge(top_watched[["movie_id"]], on="movie_id", how="inner")

        return top_watched

    def find_similar_movies(
        self, movie_id: str, df_movies: pd.DataFrame, n_recommendations: int = 10, filters: dict = None
    ) -> pd.DataFrame:
        """
        유사한 영화 찾기 (Item-Based CF 사용)

        Args:
            movie_id: 기준 영화 ID
            df_movies: 영화 정보 데이터프레임
            n_recommendations: 추천할 영화 개수 (기본값: 10)
            filters: 필터 조건 딕셔너리 (선택사항)
                - genre: 장르 리스트, 예: ["로맨스", "액션"]
                - min_year: 최소 제작연도, 예: 1988
                - max_year: 최대 제작연도, 예: 2026

        Returns:
            유사한 영화 데이터프레임 (similarity 컬럼 포함)
        """
        if self.item_based is None:
            raise ValueError("Item-Based 모델을 먼저 로드해주세요. load_item_based() 실행 필요")

        if movie_id not in df_movies["movie_id"].values:
            return pd.DataFrame()

        recommendations = self.item_based_model.predict(movie_id=movie_id, top_n=n_recommendations, return_scores=False)

        result_df = df_movies[df_movies["movie_id"].isin(recommendations)]

        if result_df is None or result_df.empty:
            return pd.DataFrame()

        # 컬럼명 통일 (similarity_score -> similarity)
        result_df = result_df.rename(columns={"similarity_score": "similarity"})

        return result_df
