"""
영화 추천 시스템 Streamlit 앱 (Firebase 통합)
"""
import streamlit as st

# 프로젝트 경로 자동 추가 (core 모듈 import 시 자동 실행)
from modules.core import add_project_paths
add_project_paths()

# Firebase 사용자 시스템 import
from user_system.firebase_config import setup_firebase_config
from user_system.firebase_auth import show_firebase_auth_ui
from streamlit_cookies_manager import EncryptedCookieManager

# 모듈 import
from modules.services import load_all_data
from modules.ui import (
    display_footer,
    inject_custom_css,
    render_app_sidebar,
    render_movie_based_recommendation,
    render_rating_management,
    render_user_based_recommendation,
)

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


def main():
    # 헤더
    st.markdown('<h1 class="main-header">🎬 볼거 없나?</h1>', unsafe_allow_html=True)
    
    # Firebase 초기화 (선택사항)
    firebase_available = setup_firebase_config()
    
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    recommendation_type, recommender = render_app_sidebar(
        firebase_available=firebase_available,
        df_movies=df_movies,
        df_ratings=df_ratings,
        global_cookies=global_cookies,
        show_auth_ui_callback=show_firebase_auth_ui,
    )
    
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
