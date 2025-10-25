"""
영화 추천 시스템 Streamlit 앱
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from streamlit_data_loader import load_movie_data, load_ratings_data, filter_data, search_movies
from streamlit_recommender import MovieRecommender

# 페이지 설정
st.set_page_config(
    page_title="볼거 없나?",
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
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s;
    }
    .movie-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .movie-title {
        font-size: 1.4rem;
        font-weight: bold;
        margin-bottom: 0.8rem;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    .movie-info {
        font-size: 0.9rem;
        opacity: 0.95;
        line-height: 1.8;
    }
    .movie-info a {
        color: #FFD700;
        text-decoration: none;
        font-weight: bold;
    }
    .movie-info a:hover {
        color: #FFF;
        text-decoration: underline;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.75rem;
    }
    .stButton>button:hover {
        background-color: #FF3333;
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
def initialize_recommender(df_movies):
    """추천 시스템 초기화 (사전 학습된 모델 로드)"""
    svd_pipeline_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_svd_pipeline.pkl'
    item_based_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_item_based.pkl'
    
    # SVD 파이프라인 확인
    if not svd_pipeline_path.exists():
        st.error("❌ SVD 파이프라인이 없습니다. 먼저 modeling/run_svd_pipeline.py를 실행해주세요.")
        st.stop()
    
    # Item-Based 모델 확인
    if not item_based_path.exists():
        st.error("❌ Item-Based 모델이 없습니다. 먼저 modeling/run_item_based_pipeline.py를 실행해주세요.")
        st.stop()
    
    with st.spinner("추천 모델을 로딩하는 중..."):
        try:
            # MovieRecommender 생성 및 모델 로드
            recommender = MovieRecommender(
                svd_pipeline_path=str(svd_pipeline_path),
                item_based_path=str(item_based_path)
            )
            
            st.success("✅ 모델 로드 완료!")
            return recommender
        except Exception as e:
            st.error(f"❌ 모델 로드 실패: {e}")
            st.stop()


def display_movie_card(movie, score=None, score_label="예측 평점", show_plot=True):
    """영화 카드 디스플레이 (풍부한 메타데이터 포함)"""
    score_text = f" | 🔮 {score_label}: {score:.2f}" if score else ""
    
    # 영화 제목 (title 또는 movie_title 컬럼 사용)
    title = movie.get('title') if pd.notna(movie.get('title')) else movie.get('movie_title', 'N/A')
    
    # 기본 정보
    year = int(movie['year']) if pd.notna(movie.get('year')) else 'N/A'
    genre = movie.get('genre', 'N/A') if pd.notna(movie.get('genre')) else 'N/A'
    country = movie.get('country', 'N/A') if pd.notna(movie.get('country')) else 'N/A'
    runtime = f"{movie['runtime']}분" if pd.notna(movie.get('runtime')) else 'N/A'
    age_rating = movie.get('age_rating', 'N/A') if pd.notna(movie.get('age_rating')) else 'N/A'
    avg_score = f"{movie['avg_score']:.1f}/5.0" if pd.notna(movie.get('avg_score')) else 'N/A'
    popularity = f"{movie['popularity']:.0f}" if pd.notna(movie.get('popularity')) else 'N/A'
    review_count = f"{movie['review_count']}개" if pd.notna(movie.get('review_count')) else 'N/A'
    
    # 왓챠피디아 링크
    movie_id = movie.get('movie_id', '')
    watcha_link = f"https://pedia.watcha.com/ko-KR/contents/{movie_id}"
    
    st.markdown(f"""
    <div class="movie-card">
        <div class="movie-title">🎬 {title}</div>
        <div class="movie-info">
            📅 개봉년도: {year} | 🎭 장르: {genre} | 🌍 국가: {country}<br>
            ⏱️ 러닝타임: {runtime} | 🔞 관람등급: {age_rating}<br>
            ⭐ 평균 평점: {avg_score} | 🔥 인기점수: {popularity} | 💬 리뷰수: {review_count}{score_text}<br>
            <a href="{watcha_link}" target="_blank" style="color: #FFD700;">🔗 왓챠피디아에서 보기</a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 출연진 정보
    if pd.notna(movie.get('cast')) and movie.get('cast'):
        with st.expander("🎭 출연진"):
            st.write(movie['cast'])
    
    # 줄거리
    if show_plot and pd.notna(movie.get('plot')) and movie.get('plot'):
        with st.expander("📖 줄거리"):
            st.write(movie['plot'])


def main():
    # 헤더
    st.markdown('<h1 class="main-header">🎬 볼거 없나?</h1>', unsafe_allow_html=True)
    
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    # 사이드바
    st.sidebar.title("⚙️ 설정")
    st.sidebar.markdown("---")
    
    # 추천 방식 선택
    recommendation_type = st.sidebar.selectbox(
        "추천 방식 선택",
        ["🎞️ 영화 기반 추천", "🎯 사용자 기반 추천"]
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
    recommender = initialize_recommender(df_movies)
    
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
                top_watched, recommendations = recommender.recommend_for_user(
                    selected_user, df_movies, n_recommendations
                )
                
                if recommendations.empty:
                    st.warning("추천할 영화가 없습니다.")
                else:
                    st.success(f"**{n_recommendations}개**의 영화를 추천합니다!")
                    
                    # 사용자가 재밌게 본 영화 표시
                    st.markdown("### 🌟 이 사용자가 재밌게 본 영화")
                    st.markdown(f"*사용자의 높은 평점 순 상위 {len(top_watched)}개*")
                    
                    for idx, row in enumerate(top_watched.iterrows(), 1):
                        _, movie = row
                        # title 또는 movie_title 컬럼 사용
                        movie_title = movie.get('title') if pd.notna(movie.get('title')) else movie.get('movie_title', 'N/A')
                        st.markdown(f"#### {idx}. {movie_title}")
                        display_movie_card(movie, movie['rating'], "내 평점", show_plot=False)
                    
                    st.markdown("---")
                    st.markdown("### 🎁 AI 추천 영화")
                    st.markdown(f"*아직 안 본 영화 중 예상 평점이 높은 순 {len(recommendations)}개*")
                    
                    for idx, row in enumerate(recommendations.iterrows(), 1):
                        _, movie = row
                        # title 또는 movie_title 컬럼 사용
                        movie_title = movie.get('title') if pd.notna(movie.get('title')) else movie.get('movie_title', 'N/A')
                        st.markdown(f"#### {idx}. {movie_title}")
                        display_movie_card(movie, movie['predicted_rating'], "예측 평점", show_plot=True)
    
    elif recommendation_type == "🎞️ 영화 기반 추천":
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

