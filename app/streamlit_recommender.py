"""
Streamlit용 추천 시스템 wrapper
Streamlit 데코레이터를 적용한 버전
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from modeling.models.recommender import MovieRecommender as _MovieRecommender


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
