"""
영화 추천 시스템 Streamlit 앱
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import pickle
import os

# 현재 디렉토리를 path에 추가
sys.path.append(str(Path(__file__).parent))

from utils.data_loader import load_movie_data, load_ratings_data, filter_data, search_movies
from utils.recommender_lite import MovieRecommenderLite

# 페이지 설정
st.set_page_config(
    page_title="🎬 영화 추천 시스템",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
        margin-bottom: 2rem;
    }
    .movie-card {
        padding: 1.5rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .movie-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .movie-info {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_all_data():
    """모든 데이터 로딩"""
    with st.spinner("데이터를 로딩하는 중..."):
        df_movies = load_movie_data()
        df_ratings = load_ratings_data()
        df_ratings_filtered = filter_data(df_ratings, min_user_ratings=30, min_movie_ratings=10)
        return df_movies, df_ratings, df_ratings_filtered


@st.cache_resource
def initialize_recommender(df_ratings_filtered, df_movies):
    """추천 시스템 초기화 (사전 학습된 모델 로드)"""
    model_path = Path(__file__).parent / 'models' / 'recommender_model.pkl'
    
    # 사전 학습된 모델이 있으면 로드
    if model_path.exists():
        with st.spinner("학습된 추천 모델을 로딩하는 중..."):
            try:
                with open(model_path, 'rb') as f:
                    recommender = pickle.load(f)
                st.success("✅ 모델 로드 완료!")
                return recommender
            except Exception as e:
                st.warning(f"모델 로드 실패: {e}. 새로 학습합니다.")
    
    # 모델이 없으면 학습 (경량화 버전)
    with st.spinner("추천 시스템을 학습하는 중... (최초 1회, 약 1-2분 소요)"):
        recommender = MovieRecommenderLite()
        recommender.train_collaborative_filtering(df_ratings_filtered, n_factors=50)
        recommender.train_content_based(df_movies)
        return recommender


def display_movie_card(movie, score=None, score_label="예측 평점"):
    """영화 카드 디스플레이"""
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-title">🎬 {movie['title']}</div>
        <div class="movie-info">
            📅 개봉년도: {int(movie['year']) if pd.notna(movie['year']) else 'N/A'} | 
            🎭 장르: {movie['genre'] if pd.notna(movie['genre']) else 'N/A'}<br>
            ⭐ 평균 평점: {movie['avg_score']:.1f}/5.0
            {f" | 🔮 {score_label}: {score:.2f}" if score else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    # 헤더
    st.markdown('<h1 class="main-header">🎬 영화 추천 시스템</h1>', unsafe_allow_html=True)
    
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    # 사이드바
    st.sidebar.title("⚙️ 설정")
    st.sidebar.markdown("---")
    
    # 추천 방식 선택
    recommendation_type = st.sidebar.selectbox(
        "추천 방식 선택",
        ["🎯 사용자 기반 추천", "🎞️ 영화 기반 추천", "✨ 하이브리드 추천"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    ### 📊 데이터 통계
    - 전체 영화 수: **{len(df_movies):,}개**
    - 전체 평점 수: **{len(df_ratings):,}개**
    - 사용자 수: **{df_ratings['user_id'].nunique():,}명**
    - 평균 평점: **{df_ratings['rating'].mean():.2f}/5.0**
    """)
    
    # 추천 시스템 초기화
    recommender = initialize_recommender(df_ratings_filtered, df_movies)
    
    # 메인 컨텐츠
    if recommendation_type == "🎯 사용자 기반 추천":
        st.header("🎯 사용자 기반 추천")
        st.markdown("특정 사용자의 과거 평점을 분석하여 맞춤형 영화를 추천합니다.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 사용자 목록
            user_list = df_ratings_filtered['user_id'].unique()[:100]  # 처음 100명만
            selected_user = st.selectbox(
                "사용자를 선택하세요",
                user_list,
                help="추천을 받을 사용자를 선택하세요"
            )
        
        with col2:
            n_recommendations = st.slider("추천 개수", 5, 20, 10)
        
        if st.button("🎬 추천 받기", key="user_rec"):
            with st.spinner("추천 영화를 찾는 중..."):
                recommendations = recommender.recommend_for_user(
                    selected_user, df_movies, df_ratings_filtered, n_recommendations
                )
                
                if recommendations.empty:
                    st.warning("추천할 영화가 없습니다.")
                else:
                    st.success(f"**{n_recommendations}개**의 영화를 추천합니다!")
                    
                    # 사용자가 본 영화 표시
                    user_movies = df_ratings[df_ratings['user_id'] == selected_user].sort_values('rating', ascending=False).head(5)
                    
                    with st.expander("👤 이 사용자가 높게 평가한 영화 Top 5"):
                        for _, movie in user_movies.iterrows():
                            st.markdown(f"- **{movie['movie_title']}** (⭐ {movie['rating']:.1f})")
                    
                    st.markdown("### 🎁 추천 영화")
                    for idx, row in recommendations.iterrows():
                        display_movie_card(row, row['predicted_rating'], "예측 평점")
    
    elif recommendation_type == "🎞️ 영화 기반 추천":
        st.header("🎞️ 영화 기반 추천")
        st.markdown("좋아하는 영화와 비슷한 영화를 찾아드립니다.")
        
        # 영화 검색
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "영화 제목을 검색하세요",
                placeholder="예: 타이타닉, 어벤져스, 기생충..."
            )
        
        with col2:
            similarity_method = st.selectbox(
                "유사도 방법",
                ["컨텐츠 기반", "협업 필터링"],
                help="컨텐츠 기반: 장르, 줄거리 유사도\n협업 필터링: 사용자 평점 패턴 유사도"
            )
        
        method = 'content' if similarity_method == "컨텐츠 기반" else 'collaborative'
        
        if search_query:
            search_results = search_movies(df_movies, search_query, limit=10)
            
            if not search_results.empty:
                selected_movie_title = st.selectbox(
                    "영화를 선택하세요",
                    search_results['title'].tolist()
                )
                
                selected_movie = search_results[search_results['title'] == selected_movie_title].iloc[0]
                
                # 선택한 영화 정보 표시
                st.markdown("### 📽️ 선택한 영화")
                display_movie_card(selected_movie)
                
                if 'plot' in selected_movie and pd.notna(selected_movie['plot']):
                    with st.expander("📖 줄거리"):
                        st.write(selected_movie['plot'])
                
                n_recommendations = st.slider("추천 개수", 5, 15, 10)
                
                if st.button("🎬 비슷한 영화 찾기", key="movie_rec"):
                    with st.spinner("비슷한 영화를 찾는 중..."):
                        similar_movies = recommender.find_similar_movies(
                            selected_movie['movie_id'], df_movies, n_recommendations, method
                        )
                        
                        if similar_movies.empty:
                            st.warning("유사한 영화를 찾을 수 없습니다.")
                        else:
                            st.success(f"**{len(similar_movies)}개**의 비슷한 영화를 찾았습니다!")
                            st.markdown("### 🎁 추천 영화")
                            
                            for idx, row in similar_movies.iterrows():
                                display_movie_card(row, row['similarity'], "유사도")
            else:
                st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
    
    else:  # 하이브리드 추천
        st.header("✨ 하이브리드 추천")
        st.markdown("협업 필터링과 컨텐츠 기반 추천을 결합한 고급 추천 시스템입니다.")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            user_list = df_ratings_filtered['user_id'].unique()[:100]
            selected_user = st.selectbox(
                "사용자를 선택하세요",
                user_list,
                key="hybrid_user"
            )
        
        with col2:
            cf_weight = st.slider("협업 필터링 가중치", 0.0, 1.0, 0.6, 0.1)
        
        with col3:
            cb_weight = 1.0 - cf_weight
            st.metric("컨텐츠 기반 가중치", f"{cb_weight:.1f}")
        
        n_recommendations = st.slider("추천 개수", 5, 20, 10, key="hybrid_n")
        
        if st.button("🎬 하이브리드 추천 받기", key="hybrid_rec"):
            with st.spinner("최적의 영화를 찾는 중..."):
                recommendations = recommender.hybrid_recommend(
                    selected_user, df_movies, df_ratings_filtered, 
                    n_recommendations, cf_weight, cb_weight
                )
                
                if recommendations.empty:
                    st.warning("추천할 영화가 없습니다.")
                else:
                    st.success(f"**{n_recommendations}개**의 영화를 추천합니다!")
                    
                    # 사용자가 본 영화 표시
                    user_movies = df_ratings[df_ratings['user_id'] == selected_user].sort_values('rating', ascending=False).head(5)
                    
                    with st.expander("👤 이 사용자가 높게 평가한 영화 Top 5"):
                        for _, movie in user_movies.iterrows():
                            st.markdown(f"- **{movie['movie_title']}** (⭐ {movie['rating']:.1f})")
                    
                    st.markdown("### 🎁 추천 영화")
                    for idx, row in recommendations.iterrows():
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            display_movie_card(row, row['hybrid_score'], "하이브리드 점수")
                        
                        with col_b:
                            st.metric("협업 점수", f"{row['cf_score']:.2f}")
                            st.metric("컨텐츠 점수", f"{row['cb_score']:.2f}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 2rem;'>
        <p>🎬 영화 추천 시스템 | 데이터 출처: Watcha</p>
        <p>Powered by Streamlit & Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

