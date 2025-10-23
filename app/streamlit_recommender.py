"""
Streamlit용 추천 시스템 wrapper
Streamlit 데코레이터를 적용한 버전
"""
import streamlit as st
from modeling.models.recommender import MovieRecommender as _MovieRecommender


class MovieRecommender(_MovieRecommender):
    """Streamlit용 추천 시스템 클래스 (캐싱 적용)"""
    
    @st.cache_resource
    def train_collaborative_filtering(self, df_ratings, n_factors: int = 20):
        """협업 필터링 모델 학습 (Streamlit 캐싱 적용)"""
        return super().train_collaborative_filtering(df_ratings, n_factors)
    
    @st.cache_resource
    def train_content_based(self, df_movies):
        """컨텐츠 기반 필터링 학습 (Streamlit 캐싱 적용)"""
        return super().train_content_based(df_movies)
