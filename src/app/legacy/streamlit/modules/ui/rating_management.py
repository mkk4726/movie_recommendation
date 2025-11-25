"""
평점 관리 UI
"""
import streamlit as st

from cold_start.show_random_movies import get_random_popular_movies
from modules.data import search_movies
from modules.ui.components import display_movie_card
from user_system.firebase_auth import require_firebase_auth
from user_system.firebase_firestore import FirestoreManager


def render_rating_management(df_movies, df_ratings, global_cookies):
    """
    평점 관리 페이지 렌더링

    Args:
        df_movies: 영화 데이터프레임
        df_ratings: 평점 데이터프레임
        global_cookies: EncryptedCookieManager 인스턴스
    """
    st.header("⭐ 내 영화 평점 관리")
    st.markdown("본 영화에 대한 평점을 입력하고 관리하세요.")

    try:
        user = require_firebase_auth(cookies=global_cookies)
        if not user:
            st.error("로그인이 필요합니다.")
            st.info("평점 관리를 사용하려면 로그인해주세요.")
            return

        firestore_manager = FirestoreManager()

        st.subheader("🎬 영화 평점 입력")
        input_method = st.radio(
            "평점 입력 방식 선택",
            ["🔍 검색", "🎲 탐색"],
            help="영화를 찾는 방식을 선택하세요",
        )

        if input_method == "🔍 검색":
            _render_search_based_rating_input(df_movies, user, firestore_manager)
        elif input_method == "🎲 탐색":
            _render_exploration_based_rating_input(df_movies, df_ratings, user, firestore_manager)

        st.markdown("---")
        st.subheader("📋 내 평점 목록")
        _render_user_ratings_list(df_movies, user, firestore_manager)

    except Exception as e:
        st.error(f"사용자 인증 오류: {e}")


def _render_search_based_rating_input(df_movies, user, firestore_manager):
    """검색 기반 평점 입력 UI"""
    search_query = st.text_input(
        "평점을 입력할 영화를 검색하세요",
        placeholder="예: 타이타닉, 어벤져스, 기생충...",
    )

    if search_query and search_query.strip():
        try:
            search_results = search_movies(df_movies, search_query, limit=10)

            if not search_results.empty:
                selected_movie_title = st.selectbox(
                    "영화를 선택하세요",
                    search_results["title"].tolist(),
                )

                selected_movie = search_results[search_results["title"] == selected_movie_title].iloc[0]

                st.markdown("### 📽️ 선택한 영화")
                display_movie_card(selected_movie, show_plot=True)

                st.markdown("### ⭐ 평점 입력")
                col1, col2 = st.columns([1, 1])

                with col1:
                    rating = st.slider(
                        "평점을 선택하세요",
                        min_value=0.5,
                        max_value=5.0,
                        step=0.5,
                        value=3.0,
                        format="%.1f",
                    )

                with col2:
                    st.write("")
                    st.write("")
                    if st.button("💾 평점 저장", type="primary"):
                        try:
                            success = firestore_manager.add_user_rating(
                                user["uid"],
                                selected_movie["movie_id"],
                                rating,
                            )

                            if success:
                                st.success(f"평점이 저장되었습니다! ({rating}/5.0)")
                            else:
                                st.error("평점 저장에 실패했습니다.")
                        except Exception as e:
                            st.error(f"평점 저장 중 오류가 발생했습니다: {e}")
            else:
                st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
        except Exception as e:
            st.error("검색 중 오류가 발생했습니다. 다시 시도해주세요.")


def _render_exploration_based_rating_input(df_movies, df_ratings, user, firestore_manager):
    """탐색 기반 평점 입력 UI"""
    st.markdown("인기 있는 영화들을 랜덤하게 탐색해보세요.")

    if "explored_movie_ids" not in st.session_state:
        st.session_state.explored_movie_ids = set()

    col1, col2 = st.columns([2, 1])
    with col1:
        n_movies = st.slider("표시할 영화 개수", 5, 20, 10)
    with col2:
        if st.button("🎲 새로운 영화 탐색", type="primary"):
            try:
                random_movies, _ = get_random_popular_movies(
                    df_ratings,
                    df_movies,
                    n_movies,
                    exclude_movie_ids=list(st.session_state.explored_movie_ids),
                )
                st.session_state.current_exploration = random_movies
                st.session_state.explored_movie_ids.update(random_movies["movie_id"].tolist())
            except Exception as e:
                st.error(f"영화 탐색 중 오류가 발생했습니다: {e}")

    if "current_exploration" in st.session_state and not st.session_state.current_exploration.empty:
        st.markdown("### 🎬 탐색 중인 영화들")
        st.markdown(f"*총 {len(st.session_state.current_exploration)}개의 영화*")

        for idx, (_, movie) in enumerate(st.session_state.current_exploration.iterrows(), 1):
            st.markdown(f"#### {idx}. {movie.get('title', 'N/A')}")
            display_movie_card(movie, show_plot=True)

            col_rating1, col_rating2, col_rating3 = st.columns([2, 1, 1])

            with col_rating1:
                rating = st.slider(
                    "평점을 선택하세요",
                    min_value=0.5,
                    max_value=5.0,
                    step=0.5,
                    value=3.0,
                    format="%.1f",
                    key=f"rating_{movie['movie_id']}",
                )

            with col_rating2:
                st.write("")
                st.write("")
                if st.button("💾 저장", key=f"save_{movie['movie_id']}"):
                    try:
                        success = firestore_manager.add_user_rating(
                            user["uid"],
                            movie["movie_id"],
                            rating,
                        )

                        if success:
                            st.success(f"평점이 저장되었습니다! ({rating}/5.0)")
                        else:
                            st.error("평점 저장에 실패했습니다.")
                    except Exception as e:
                        st.error(f"평점 저장 중 오류가 발생했습니다: {e}")

            with col_rating3:
                st.write("")
                st.write("")
                if st.button("⏭️ 건너뛰기", key=f"skip_{movie['movie_id']}"):
                    st.info("영화를 건너뛰었습니다.")


def _render_user_ratings_list(df_movies, user, firestore_manager):
    """사용자의 기존 평점 목록 표시"""
    try:
        user_ratings = firestore_manager.get_user_ratings(user["uid"])
        if not user_ratings:
            st.info("아직 저장된 평점이 없습니다. 영화를 평가해보세요!")
            return

        for idx, rating_info in enumerate(user_ratings, 1):
            movie_id = rating_info.get("movie_id")
            rating = rating_info.get("rating")

            movie = df_movies[df_movies["movie_id"] == movie_id]
            if movie.empty:
                continue

            movie = movie.iloc[0]
            st.markdown(f"#### {idx}. {movie.get('title', 'N/A')} - ⭐ {rating}/5.0")
            display_movie_card(movie, show_plot=False)

            if st.button("🗑️ 삭제", key=f"delete_{movie_id}"):
                try:
                    firestore_manager.delete_user_rating(user["uid"], movie_id)
                    st.success("평점이 삭제되었습니다.")
                except Exception as e:
                    st.error(f"평점 삭제 중 오류가 발생했습니다: {e}")

    except Exception as e:
        st.error(f"평점 목록을 불러오는 중 오류가 발생했습니다: {e}")
