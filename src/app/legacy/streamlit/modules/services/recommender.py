"""
Streamlit용 추천 시스템 wrapper
"""

# 경로 자동 추가
from modules.core import add_project_paths  # noqa: E402

import streamlit as st

add_project_paths()

from modeling.models.recommender import MovieRecommender as _MovieRecommender  # noqa: E402


class MovieRecommender(_MovieRecommender):
    """Streamlit용 추천 시스템 클래스 (캐싱 적용)"""

    @st.cache_resource
    def load_svd_pipeline(_self, filepath: str):
        """SVD 파이프라인 로드 (Streamlit 캐싱 적용)"""
        return super(MovieRecommender, _self).load_svd_pipeline(filepath)

    @st.cache_resource
    def load_item_based(_self, filepath: str):
        """Item-Based 모델 로드 (Streamlit 캐싱 적용)"""
        return super(MovieRecommender, _self).load_item_based(filepath)
