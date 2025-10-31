"""
사이드바 UI 렌더링 모듈
"""
import streamlit as st

from modules.services import load_recommender_models


def render_app_sidebar(
    firebase_available,
    df_movies,
    df_ratings,
    global_cookies,
    show_auth_ui_callback=None,
):
    """
    사이드바를 렌더링하고 사용자 선택 및 모델 로드 상태를 반환합니다.

    Returns:
        tuple[str, MovieRecommender]: (선택한 추천 타입, 로드된 추천기)
    """
    st.sidebar.markdown("### 🔥 Firebase 설정")
    if firebase_available:
        st.sidebar.success("✅ Firebase 연결됨")
    else:
        st.sidebar.error("❌ Firebase 연결 실패")
        st.sidebar.info("Firebase 설정이 필요합니다.")

    st.sidebar.markdown("---")
    if firebase_available and show_auth_ui_callback:
        show_auth_ui_callback(cookies=global_cookies)
    else:
        st.sidebar.info("Firebase 설정이 필요합니다.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 추천 방식")
    if firebase_available:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천", "🎯 사용자 기반 추천", "⭐ 내 평점 관리"],
            help="원하는 추천 방식을 선택하세요",
        )
    else:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천"],
            help="사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다",
        )
        st.sidebar.info("💡 사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 수집한 데이터 통계")
    st.sidebar.markdown(
        f"""
    - 전체 영화 수: **{len(df_movies):,}개**
    - 전체 평점 수: **{len(df_ratings):,}개**
    - 사용자 수: **{df_ratings['user_id'].nunique():,}명**
    - 평균 평점: **{df_ratings['rating'].mean():.2f}/5.0**
    """
    )

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
    except Exception as e:  # pragma: no cover - Streamlit 제어 플로우
        st.sidebar.error(f"❌ 모델 로드 실패: {e}")
        st.stop()

    return recommendation_type, recommender
