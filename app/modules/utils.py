"""
공통 유틸리티 함수
"""
import streamlit as st
import pandas as pd


def inject_custom_css():
    """커스텀 CSS 주입"""
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
            ⭐ 평균 평점: {avg_score} | 💬 리뷰수: {review_count}{score_text}<br>
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


def display_footer():
    """Footer 표시"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 2rem;'>
        <p>🎬 영화 추천 시스템 | 데이터 출처: Watcha</p>
        <p>Powered by Streamlit & Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)
