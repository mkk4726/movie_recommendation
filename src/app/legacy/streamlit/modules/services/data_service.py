"""
데이터 및 모델 로딩 서비스 모듈
"""

# 경로 자동 추가 및 가져오기
from modules.core import PROJECT_ROOT  # noqa: E402
from modules.data import filter_data, load_movie_data, load_ratings_data  # noqa: E402

import streamlit as st

from .recommender import MovieRecommender  # noqa: E402


@st.cache_data
def load_all_data():
    """모든 데이터 로딩"""
    with st.spinner("데이터를 로딩하는 중..."):
        df_movies = load_movie_data()
        df_ratings = load_ratings_data()
        df_ratings_filtered = filter_data(df_ratings, min_user_ratings=30, min_movie_ratings=10)
        return df_movies, df_ratings, df_ratings_filtered


@st.cache_resource
def load_recommender_models():
    """추천 모델 로드"""
    svd_pipeline_path = PROJECT_ROOT / "modeling" / "models" / "pkls" / "trained_svd_pipeline.pkl"
    item_based_path = PROJECT_ROOT / "modeling" / "models" / "pkls" / "trained_item_based.pkl"

    if not svd_pipeline_path.exists():
        raise FileNotFoundError("❌ SVD 파이프라인이 없습니다. 먼저 modeling/run_svd_pipeline.py를 실행해주세요.")

    if not item_based_path.exists():
        raise FileNotFoundError(
            "❌ Item-Based 모델이 없습니다. 먼저 modeling/run_item_based_pipeline.py를 실행해주세요."
        )

    recommender = MovieRecommender(
        svd_pipeline_path=str(svd_pipeline_path),
        item_based_path=str(item_based_path),
    )
    return recommender
