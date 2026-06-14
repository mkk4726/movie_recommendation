"""
Recommender service for FastAPI.
Provides a simple interface to MovieRecommender with caching.
"""

import logging
from functools import lru_cache
from typing import Optional, Tuple

import pandas as pd

from core.modeling.models.recommender.recommender import MovieRecommender

logger = logging.getLogger(__name__)

# 필터 적용 시 후보를 더 많이 뽑아 필터링 후 원하는 개수를 보장하기 위한 배수
_FILTER_OVERSAMPLE_FACTOR = 60


@lru_cache(maxsize=1)
def get_recommender_service() -> MovieRecommender:
    """MovieRecommender 싱글톤 인스턴스를 반환합니다."""
    logger.info("MovieRecommender 인스턴스 생성 중...")
    return MovieRecommender()


def recommend_for_user(user_id: str, df_movies: pd.DataFrame, n: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    사용자에게 영화를 추천합니다.

    Args:
        user_id: 사용자 ID
        df_movies: 영화 정보 DataFrame
        n: 추천할 영화 개수

    Returns:
        (top_watched_df, recommendations_df) 튜플
    """
    recommender = get_recommender_service()

    # 추천 영화 가져오기
    recommendations_df = recommender.recommend_for_user(user_id=user_id, df_movies=df_movies, n_recommendations=n)

    # 컬럼명 통일 (pred_rating -> predicted_rating)
    if "pred_rating" in recommendations_df.columns:
        recommendations_df = recommendations_df.rename(columns={"pred_rating": "predicted_rating"})

    # 사용자가 높게 평가한 영화 가져오기
    try:
        top_watched = recommender.df_trainset.loc[recommender.df_trainset["user_id"] == user_id].nlargest(n, "rating")

        if not top_watched.empty:
            top_watched_df = df_movies.merge(
                top_watched[["movie_id", "rating"]], on="movie_id", how="inner"
            ).sort_values("rating", ascending=False)
        else:
            top_watched_df = pd.DataFrame()
    except Exception as e:
        logger.warning(f"사용자 top watched 가져오기 실패: {e}")
        top_watched_df = pd.DataFrame()

    return top_watched_df, recommendations_df


def similar_movies(
    movie_id: str, df_movies: pd.DataFrame, n_recommendations: int = 10, filters: Optional[dict] = None
) -> pd.DataFrame:
    """
    유사한 영화를 찾습니다.

    Args:
        movie_id: 기준 영화 ID
        df_movies: 영화 정보 DataFrame
        n_recommendations: 추천할 영화 개수
        filters: 필터 조건 딕셔너리 (선택사항)

    Returns:
        유사한 영화 DataFrame (similarity 컬럼 포함)
    """
    recommender = get_recommender_service()

    # 유사도 점수 포함해서 가져오기
    try:
        fetch_n = n_recommendations * _FILTER_OVERSAMPLE_FACTOR if filters else n_recommendations

        similar_scores_df = recommender.item_based_model.predict(movie_id=movie_id, top_n=fetch_n, return_scores=True)

        if similar_scores_df is None or similar_scores_df.empty:
            return pd.DataFrame()

        # 영화 정보와 병합
        similar_df = df_movies.merge(similar_scores_df[["movie_id", "similarity_score"]], on="movie_id", how="inner")

        # similarity_score를 similarity로 이름 변경
        similar_df = similar_df.rename(columns={"similarity_score": "similarity"})

    except Exception as e:
        logger.warning(f"item_based_model.predict 실패: {e}")
        return pd.DataFrame()

    if similar_df.empty:
        return similar_df

    # 필터 적용
    if filters:
        # 장르 필터
        if "genre" in filters and filters["genre"]:
            genre_list = filters["genre"]
            if isinstance(genre_list, str):
                genre_list = [genre_list]
            if "genres_tmdb" in similar_df.columns:
                genre_mask = similar_df["genres_tmdb"].apply(
                    lambda x: any(g in str(x) for g in genre_list) if pd.notna(x) else False
                )
                similar_df = similar_df[genre_mask]

        # 연도 필터
        if "min_year" in filters and filters["min_year"] is not None:
            if "year" in similar_df.columns:
                similar_df = similar_df[similar_df["year"] >= filters["min_year"]]

        if "max_year" in filters and filters["max_year"] is not None:
            if "year" in similar_df.columns:
                similar_df = similar_df[similar_df["year"] <= filters["max_year"]]

        # 언어 필터
        if "language" in filters and filters["language"]:
            language_list = filters["language"]
            if isinstance(language_list, str):
                language_list = [language_list]
            if "language" in similar_df.columns:
                language_mask = similar_df["language"].apply(
                    lambda x: any(lang in str(x) for lang in language_list) if pd.notna(x) else False
                )
                similar_df = similar_df[language_mask]

    # similarity 기준으로 정렬
    if "similarity" in similar_df.columns:
        similar_df = similar_df.sort_values("similarity", ascending=False)

    # 최종 개수 제한
    similar_df = similar_df.head(n_recommendations)

    return similar_df.reset_index(drop=True)

