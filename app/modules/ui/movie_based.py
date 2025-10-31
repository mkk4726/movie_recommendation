"""
영화 기반 추천 UI
"""
import pandas as pd
import streamlit as st

# 경로 자동 추가
from modules.core import add_project_paths  # noqa: E402
add_project_paths()

from modules.config import COUNTRY_OPTIONS, GENRE_OPTIONS, MAX_YEAR, MIN_YEAR  # noqa: E402
from modules.data import search_movies  # noqa: E402
from modules.ui.components import display_movie_card  # noqa: E402


def render_movie_based_recommendation(recommender, df_movies):
    """
    영화 기반 추천 페이지 렌더링

    Args:
        recommender: MovieRecommender 인스턴스
        df_movies: 영화 데이터프레임
    """
    st.header("🎞️ 영화 기반 추천")
    st.markdown("좋아하는 영화와 비슷한 영화를 찾아드립니다. (Item-Based CF 사용)")

    search_query = st.text_input(
        "영화 제목을 검색하세요",
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
                selected_title = (
                    selected_movie.get("title")
                    if pd.notna(selected_movie.get("title"))
                    else selected_movie.get("movie_title", "N/A")
                )
                st.markdown(f"**{selected_title}**")
                display_movie_card(selected_movie, show_plot=True)

                with st.form("recommendation_form", clear_on_submit=False):
                    col_rec1, col_rec2, col_rec3, col_rec4 = st.columns([3, 2, 2, 3])

                    with col_rec1:
                        n_recommendations = st.slider("추천 개수", 5, 15, 10, key="movie_slider")

                    with col_rec2:
                        selected_genres = st.multiselect(
                            "장르 선택",
                            options=GENRE_OPTIONS,
                            default=[],
                            key="movie_genre_filter",
                        )

                    with col_rec3:
                        selected_countries = st.multiselect(
                            "국가 선택",
                            options=COUNTRY_OPTIONS,
                            default=[],
                            key="movie_country_filter",
                        )

                    with col_rec4:
                        min_year = MIN_YEAR
                        max_year = MAX_YEAR
                        selected_year_range = st.slider(
                            "선호하는 제작연도 범위",
                            min_value=min_year,
                            max_value=max_year,
                            value=(min_year, max_year),
                            step=1,
                            key="movie_year_slider",
                        )

                    submitted = st.form_submit_button("🎬 비슷한 영화 찾기", use_container_width=True)

                if submitted:
                    filter_dict = {}
                    if selected_genres:
                        filter_dict["genre"] = selected_genres
                    if selected_year_range:
                        min_year, max_year = selected_year_range
                        filter_dict["min_year"] = min_year
                        filter_dict["max_year"] = max_year
                    if selected_countries:
                        filter_dict["country"] = selected_countries

                    filter_dict = filter_dict if filter_dict else None

                    with st.spinner("비슷한 영화를 찾는 중..."):
                        similar_movies = recommender.find_similar_movies(
                            selected_movie["movie_id"], df_movies, n_recommendations, filters=filter_dict
                        )

                        if similar_movies.empty:
                            st.warning("유사한 영화를 찾을 수 없습니다.")
                        else:
                            st.success(f"**{n_recommendations}개**의 비슷한 영화를 찾았습니다!")

                            st.markdown("---")
                            st.markdown("### 🎁 비슷한 영화 추천")
                            st.markdown(f"*평점 패턴 기반으로 찾은 유사한 영화 {len(similar_movies)}개*")

                            for idx, row in enumerate(similar_movies.iterrows(), 1):
                                _, movie = row
                                movie_title = (
                                    movie.get("title")
                                    if pd.notna(movie.get("title"))
                                    else movie.get("movie_title", "N/A")
                                )
                                st.markdown(f"#### {idx}. {movie_title}")
                                display_movie_card(movie, movie["similarity"], "유사도", show_plot=True)
            else:
                st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
        except Exception as e:
            st.error("검색 중 오류가 발생했습니다. 다시 시도해주세요.")
            st.error(f"오류 상세: {str(e)}")
