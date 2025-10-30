"""
영화 추천 시스템 Streamlit 앱 (Firebase 통합)
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from modules.data_loader import load_movie_data, load_ratings_data, filter_data
from modules.recommender import MovieRecommender

# Firebase 사용자 시스템 import
from user_system.firebase_config import setup_firebase_config
from user_system.firebase_auth import show_firebase_auth_ui
from streamlit_cookies_manager import EncryptedCookieManager

# 모듈 import
from modules.utils import inject_custom_css, display_footer
from modules.movie_based_recommendation import render_movie_based_recommendation
from modules.user_based_recommendation import render_user_based_recommendation
from modules.rating_management import render_rating_management

# 페이지 설정
st.set_page_config(
    page_title="볼거 없나?",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 CookieManager 인스턴스 생성 (앱 전체에서 한 번만 생성)
# 주의: @st.cache_resource 사용 금지 - EncryptedCookieManager는 내부적으로 Streamlit 위젯을 생성함
global_cookies = EncryptedCookieManager(
    password="movie_recommendation_secret_key_2024",
    prefix="firebase_"
)

# 쿠키가 준비되지 않았으면 대기
if not global_cookies.ready():
    st.stop()

# 커스텀 CSS 주입
inject_custom_css()


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
    """모델 로드 (UI 없이 순수 로직만)"""
    svd_pipeline_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_svd_pipeline.pkl'
    item_based_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_item_based.pkl'
    
    # 파일 존재 확인
    if not svd_pipeline_path.exists():
        raise FileNotFoundError("❌ SVD 파이프라인이 없습니다. 먼저 modeling/run_svd_pipeline.py를 실행해주세요.")
    
    if not item_based_path.exists():
        raise FileNotFoundError("❌ Item-Based 모델이 없습니다. 먼저 modeling/run_item_based_pipeline.py를 실행해주세요.")
    
    # 모델 로드
    recommender = MovieRecommender(
        svd_pipeline_path=str(svd_pipeline_path),
        item_based_path=str(item_based_path)
    )
    return recommender

def main():
    # 헤더
    st.markdown('<h1 class="main-header">🎬 볼거 없나?</h1>', unsafe_allow_html=True)
    
    # Firebase 초기화 (선택사항)
    firebase_available = setup_firebase_config()
    
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    

    st.sidebar.markdown("### 🔥 Firebase 설정")
    if firebase_available:
        st.sidebar.success("✅ Firebase 연결됨")
    else:
        st.sidebar.error("❌ Firebase 연결 실패")
        st.sidebar.info("Firebase 설정이 필요합니다.")

    st.sidebar.markdown("---")
    if firebase_available:
        show_firebase_auth_ui(cookies=global_cookies)
    else:
        st.sidebar.info("Firebase 설정이 필요합니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 추천 방식")
    if firebase_available:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천", "🎯 사용자 기반 추천", "⭐ 내 평점 관리"],
            help="원하는 추천 방식을 선택하세요"
        )
    else:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천"],
            help="사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다"
        )
        st.sidebar.info("💡 사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 수집한 데이터 통계")
    st.sidebar.markdown(f"""
    - 전체 영화 수: **{len(df_movies):,}개**
    - 전체 평점 수: **{len(df_ratings):,}개**
    - 사용자 수: **{df_ratings['user_id'].nunique():,}명**
    - 평균 평점: **{df_ratings['rating'].mean():.2f}/5.0**
    """)
    
    # 추천 시스템 초기화 (사이드바 UI와 함께)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 추천 모델 로드 상태")
    
    try:
        with st.sidebar:
            with st.spinner("모델을 불러오는 중..."):
                recommender = load_recommender_models()
                st.success("✅ 모델 로드 완료!")
                st.caption("모델이 성공적으로 초기화되었습니다.")
    except FileNotFoundError as e:
        st.sidebar.error(str(e))
        st.stop()
    except Exception as e:
        st.sidebar.error(f"❌ 모델 로드 실패: {e}")
        st.stop()
    
    # 메인 컨텐츠 - 모듈화된 기능 라우팅
    if recommendation_type == "⭐ 내 평점 관리":
        if not firebase_available:
            st.error("❌ Firebase가 설정되지 않았습니다.")
            st.info("평점 관리를 사용하려면 Firebase 설정이 필요합니다.")
        else:
            render_rating_management(df_movies, df_ratings, global_cookies)
    
    elif recommendation_type == "🎯 사용자 기반 추천":
        if not firebase_available:
            st.error("❌ Firebase가 설정되지 않았습니다.")
            st.info("사용자 기반 추천을 사용하려면 Firebase 설정이 필요합니다.")
        else:
            render_user_based_recommendation(recommender, df_movies, df_ratings_filtered, global_cookies)
    
    elif recommendation_type == "🎞️ 영화 기반 추천":
        render_movie_based_recommendation(recommender, df_movies)
    
    # Footer
    display_footer()


if __name__ == "__main__":
    main()

