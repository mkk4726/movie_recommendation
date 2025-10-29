"""
영화 기반 추천 모듈
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
app_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(app_dir))

from modules.data_loader import search_movies
from modules.utils import display_movie_card


def render_movie_based_recommendation(recommender, df_movies):
    """
    영화 기반 추천 페이지 렌더링
    
    Args:
        recommender: MovieRecommender 인스턴스
        df_movies: 영화 데이터프레임
    """
    st.header("🎞️ 영화 기반 추천")
    st.markdown("좋아하는 영화와 비슷한 영화를 찾아드립니다. (Item-Based CF 사용)")
    
    # 영화 검색
    search_query = st.text_input(
        "영화 제목을 검색하세요",
        placeholder="예: 타이타닉, 어벤져스, 기생충..."
    )
    
    if search_query and search_query.strip():
        try:
            search_results = search_movies(df_movies, search_query, limit=10)
            
            if not search_results.empty:
                selected_movie_title = st.selectbox(
                    "영화를 선택하세요",
                    search_results['title'].tolist()
                )
                
                selected_movie = search_results[search_results['title'] == selected_movie_title].iloc[0]
                
                # 선택한 영화 정보 표시
                st.markdown("### 📽️ 선택한 영화")
                # title 또는 movie_title 컬럼 사용
                selected_title = selected_movie.get('title') if pd.notna(selected_movie.get('title')) else selected_movie.get('movie_title', 'N/A')
                st.markdown(f"**{selected_title}**")
                display_movie_card(selected_movie, show_plot=True)
                
                col_rec1, col_rec2 = st.columns([2, 1])
                with col_rec1:
                    n_recommendations = st.slider("추천 개수", 5, 15, 10, key="movie_slider")
                with col_rec2:
                    st.write("")  # spacing
                
                if st.button("🎬 비슷한 영화 찾기", key="movie_rec"):
                    with st.spinner("비슷한 영화를 찾는 중..."):
                        similar_movies = recommender.find_similar_movies(
                            selected_movie['movie_id'], df_movies, n_recommendations
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
                                # title 또는 movie_title 컬럼 사용
                                movie_title = movie.get('title') if pd.notna(movie.get('title')) else movie.get('movie_title', 'N/A')
                                st.markdown(f"#### {idx}. {movie_title}")
                                display_movie_card(movie, movie['similarity'], "유사도", show_plot=True)
            else:
                st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
        except Exception as e:
            st.error("검색 중 오류가 발생했습니다. 다시 시도해주세요.")
            st.error(f"오류 상세: {str(e)}")
