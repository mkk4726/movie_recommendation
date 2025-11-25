"""
사용자 기반 추천 UI
"""

import pandas as pd
from modules.ui.components import display_movie_card

import streamlit as st
from user_system.firebase_auth import require_firebase_auth


def render_user_based_recommendation(recommender, df_movies, df_ratings_filtered, global_cookies):
    """
    사용자 기반 추천 페이지 렌더링

    Args:
        recommender: MovieRecommender 인스턴스
        df_movies: 영화 데이터프레임
        df_ratings_filtered: 필터링된 평점 데이터프레임
        global_cookies: EncryptedCookieManager 인스턴스
    """
    st.header("🎯 사용자 기반 추천")
    st.markdown("특정 사용자의 과거 평점을 분석하여 맞춤형 영화를 추천합니다.")

    try:
        user = require_firebase_auth(cookies=global_cookies)
        if not user:
            st.error("로그인이 필요합니다.")
            st.info("사용자 기반 추천을 받으려면 로그인해주세요.")
            return

        col1, col2 = st.columns([3, 1])

        with col1:
            user_option = st.radio(
                "추천 받을 사용자 선택",
                ["👤 나 (현재 로그인된 사용자)", "👥 다른 사용자"],
                help="추천을 받을 사용자를 선택하세요",
            )

            if user_option == "👤 나 (현재 로그인된 사용자)":
                selected_user = user["uid"]
                st.info(f"현재 사용자: {user.get('display_name', 'User')}")
            else:
                user_list = df_ratings_filtered["user_id"].unique()[:100]
                selected_user = st.selectbox(
                    "사용자를 선택하세요",
                    user_list,
                    help="추천을 받을 사용자를 선택하세요",
                )

        with col2:
            n_recommendations = st.slider("추천 개수", 5, 20, 10)

        if st.button("🎬 추천 받기", key="user_rec"):
            with st.spinner("추천 영화를 찾는 중..."):
                try:
                    top_watched, recommendations = recommender.recommend_for_user(
                        selected_user, df_movies, n_recommendations
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "나 (현재 로그인된 사용자)" in user_option and (
                        "찾을 수 없습니다" in error_msg or "KeyError" in error_msg
                    ):
                        st.warning("⚠️ 아직 학습되기 전입니다.")
                        st.info(
                            """
                        **더 좋은 개인화 추천을 받으려면:**
                        1. 영화 평점을 더 많이 입력해주세요
                        2. 최소 10개 이상의 평점이 필요합니다
                        3. 평점 관리 탭에서 영화를 검색하여 평점을 입력해보세요

                        **📚 학습 시스템 안내:**
                        - 학습 주기는 **1주일**입니다 (입력하신 데이터는 1주일 이내에 학습될 예정입니다)
                        - 매주 새로운 평점 데이터로 추천 모델이 업데이트됩니다
                        - 더 많은 평점을 입력할수록 더 정확한 추천을 받을 수 있습니다
                        """
                        )
                        return
                    else:
                        st.error(f"추천 생성 중 오류가 발생했습니다: {e}")
                        return

                if recommendations.empty:
                    st.warning("추천할 영화가 없습니다.")
                else:
                    st.success(f"**{n_recommendations}개**의 영화를 추천합니다!")

                    with st.expander(f"🌟 이 사용자가 재밌게 본 영화 (상위 {len(top_watched)}개)", expanded=False):
                        for idx, row in enumerate(top_watched.iterrows(), 1):
                            _, movie = row
                            movie_title = (
                                movie.get("title") if pd.notna(movie.get("title")) else movie.get("movie_title", "N/A")
                            )
                            st.markdown(f"#### {idx}. {movie_title}")
                            display_movie_card(movie, movie["rating"], "내 평점", show_plot=True)

                    st.markdown("---")
                    st.markdown("### 🎁 AI 추천 영화")
                    st.markdown(f"*아직 안 본 영화 중 예상 평점이 높은 순 {len(recommendations)}개*")

                    for idx, row in enumerate(recommendations.iterrows(), 1):
                        _, movie = row
                        movie_title = (
                            movie.get("title") if pd.notna(movie.get("title")) else movie.get("movie_title", "N/A")
                        )
                        st.markdown(f"#### {idx}. {movie_title}")
                        display_movie_card(movie, movie["predicted_rating"], "예측 평점", show_plot=True)

    except Exception as e:
        st.error(f"사용자 인증 오류: {e}")
