"""
Streamlit용 추천 시스템 wrapper
Streamlit 데코레이터를 적용한 버전
"""
import streamlit as st
from modeling.models.recommender import MovieRecommender as _MovieRecommender


class MovieRecommender(_MovieRecommender):
    """Streamlit용 추천 시스템 클래스 (캐싱 적용)"""
    
    @st.cache_resource
    def load_svd_pipeline(_self, filepath: str):
        """SVD 파이프라인 로드 (Streamlit 캐싱 적용)"""
        return super(MovieRecommender, _self).load_svd_pipeline(filepath)
    
    @st.cache_resource
    def train_content_based(_self, df_movies):
        """컨텐츠 기반 필터링 학습 (Streamlit 캐싱 적용)"""
        return super(MovieRecommender, _self).train_content_based(df_movies)
