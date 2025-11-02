"""
영화 추천 시스템 Streamlit 앱 (Firebase 통합)
"""
import logging
import streamlit as st

# 로깅 설정 (터미널에서 확인 가능)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 프로젝트 경로 자동 추가
import sys
from pathlib import Path

# 레거시 앱의 modules를 sys.path에 추가
LEGACY_DIR = Path(__file__).parent
PROJECT_ROOT = LEGACY_DIR.parents[2]  # app/legacy/streamlit -> app -> 프로젝트 루트
sys.path.insert(0, str(LEGACY_DIR))  # legacy/streamlit/modules를 import할 수 있도록
sys.path.insert(0, str(PROJECT_ROOT))  # 프로젝트 루트도 추가

from modules.core import add_project_paths
add_project_paths()

# Firebase 사용자 시스템 import
from user_system.firebase_config import setup_firebase_config, get_firebase_manager
from user_system.firebase_auth import show_firebase_auth_ui
from streamlit_cookies_manager import EncryptedCookieManager

# 레거시 모듈 import (legacy/streamlit/modules에서)
from modules.services import load_all_data
from modules.ui import (
    display_footer,
    inject_custom_css,
    render_app_sidebar,
    render_movie_based_recommendation,
    render_rating_management,
    render_user_based_recommendation,
)

# 페이지 설정 (반드시 최상단에 위치)
st.set_page_config(
    page_title="볼거 없나?",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 CookieManager 인스턴스 생성 (앱 전체에서 한 번만 생성)
# st.session_state를 사용하여 초기화를 지연하고 중복 생성 방지
if 'global_cookies' not in st.session_state:
    try:
        st.session_state.global_cookies = EncryptedCookieManager(
            password="movie_recommendation_secret_key_2024",
            prefix="firebase_"
        )
    except Exception as e:
        st.error(f"쿠키 관리자 초기화 실패: {e}")
        st.session_state.global_cookies = None

# 쿠키 준비 상태 확인 (준비되지 않아도 앱은 계속 실행)
# 쿠키가 준비되지 않은 경우 Firebase 기능만 제한적으로 사용

# Firebase 설정 초기화 (앱 시작 시 한 번만 실행)
setup_firebase_config()

# 커스텀 CSS 주입
inject_custom_css()


def main():
    # 헤더
    st.markdown('<h1 class="main-header">🎬 볼거 없나?</h1>', unsafe_allow_html=True)
    
    # Firebase 연결 상태 확인 (매번 재확인)
    firebase_manager = get_firebase_manager()
    firebase_available = firebase_manager.initialized
    
    # 쿠키 상태 확인
    cookies_ready = (
        st.session_state.global_cookies is not None 
        and st.session_state.global_cookies.ready()
    )
        
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    recommendation_type, recommender = render_app_sidebar(
        firebase_available=firebase_available,  # Firebase 연결 상태는 쿠키와 별개로 표시
        df_movies=df_movies,
        df_ratings=df_ratings,
        global_cookies=st.session_state.global_cookies if cookies_ready else None,
        show_auth_ui_callback=show_firebase_auth_ui if cookies_ready else None,
    )
    
    # 메인 컨텐츠 - 모듈화된 기능 라우팅
    if recommendation_type == "⭐ 내 평점 관리":
        if firebase_available and cookies_ready:
            render_rating_management(df_movies, df_ratings, st.session_state.global_cookies)
    
    elif recommendation_type == "🎯 사용자 기반 추천":
        if firebase_available and cookies_ready:
            render_user_based_recommendation(recommender, df_movies, df_ratings_filtered, st.session_state.global_cookies)
    
    elif recommendation_type == "🎞️ 영화 기반 추천":
        render_movie_based_recommendation(recommender, df_movies)
    
    # Footer
    display_footer()


if __name__ == "__main__":
    main()
