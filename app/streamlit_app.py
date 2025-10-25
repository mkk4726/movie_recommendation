"""
영화 추천 시스템 Streamlit 앱 (Firebase 통합)
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
from cold_start.show_random_movies import get_random_popular_movies

# Firebase 사용자 시스템 import
from user_system.firebase_config import init_firebase, setup_firebase_config
from user_system.firebase_auth import show_firebase_auth_ui, require_firebase_auth
from user_system.firebase_firestore import FirestoreManager
from streamlit_cookies_manager import EncryptedCookieManager

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
def load_recommender_models():
    """모델 로드 (UI 없이 순수 로직만)"""
    svd_pipeline_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_svd_pipeline.pkl'
    item_based_path = project_root / 'modeling' / 'models' / 'pkls' / 'trained_item_based.pkl'
    
    # 파일 존재 확인
    if not svd_pipeline_path.exists():
        raise FileNotFoundError("❌ SVD 파이프라인이 없습니다. 먼저 modeling/run_svd_pipeline.py를 실행해주세요.")
    
    if not item_based_path.exists():
        raise FileNotFoundError("❌ Item-Based 모델이 없습니다. 먼저 modeling/run_item_based_pipeline.py를 실행해주세요.")
    
    # 모델 로드
    recommender = MovieRecommender(
        svd_pipeline_path=str(svd_pipeline_path),
        item_based_path=str(item_based_path)
    )
    return recommender

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
    
    # Firebase 초기화 (선택사항)
    firebase_available = setup_firebase_config()
    
    # 데이터 로딩
    df_movies, df_ratings, df_ratings_filtered = load_all_data()
    
    

    st.sidebar.markdown("### 🔥 Firebase 설정")
    if firebase_available:
        st.sidebar.success("✅ Firebase 연결됨")
    else:
        st.sidebar.error("❌ Firebase 연결 실패")
        st.sidebar.info("Firebase 설정이 필요합니다.")

    st.sidebar.markdown("---")
    if firebase_available:
        show_firebase_auth_ui(cookies=global_cookies)
    else:
        st.sidebar.info("Firebase 설정이 필요합니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 추천 방식")
    if firebase_available:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천", "🎯 사용자 기반 추천", "⭐ 내 평점 관리"],
            help="원하는 추천 방식을 선택하세요"
        )
    else:
        recommendation_type = st.sidebar.selectbox(
            "추천 방식 선택",
            ["🎞️ 영화 기반 추천"],
            help="사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다"
        )
        st.sidebar.info("💡 사용자 기반 추천과 평점 관리를 사용하려면 Firebase 설정이 필요합니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 데이터 통계")
    st.sidebar.markdown(f"""
    - 전체 영화 수: **{len(df_movies):,}개**
    - 전체 평점 수: **{len(df_ratings):,}개**
    - 사용자 수: **{df_ratings['user_id'].nunique():,}명**
    - 평균 평점: **{df_ratings['rating'].mean():.2f}/5.0**
    """)
    
    # 추천 시스템 초기화 (사이드바 UI와 함께)
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
    except Exception as e:
        st.sidebar.error(f"❌ 모델 로드 실패: {e}")
        st.stop()
    
    # 메인 컨텐츠
    if recommendation_type == "⭐ 내 평점 관리":
        st.header("⭐ 내 영화 평점 관리")
        st.markdown("본 영화에 대한 평점을 입력하고 관리하세요.")
        
        # Firebase 사용 가능 여부 확인
        if not firebase_available:
            st.error("❌ Firebase가 설정되지 않았습니다.")
            st.info("평점 관리를 사용하려면 Firebase 설정이 필요합니다.")
            return
        
        try:
            # 사용자 인증 확인
            user = require_firebase_auth(cookies=global_cookies)
            if not user:
                st.error("로그인이 필요합니다.")
                st.info("평점 관리를 사용하려면 로그인해주세요.")
                return
            
            # Firestore 매니저 초기화
            firestore_manager = FirestoreManager()
            
            # 평점 입력 방식 선택
            st.subheader("🎬 영화 평점 입력")
            input_method = st.radio(
                "평점 입력 방식 선택",
                ["🔍 검색", "🎲 탐색"],
                help="영화를 찾는 방식을 선택하세요"
            )
            
            if input_method == "🔍 검색":
                # 영화 검색 및 평점 입력
                search_query = st.text_input(
                    "평점을 입력할 영화를 검색하세요",
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
                            display_movie_card(selected_movie, show_plot=True)
                            
                            # 평점 입력
                            st.markdown("### ⭐ 평점 입력")
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                rating = st.slider(
                                    "평점을 선택하세요",
                                    min_value=0.5,
                                    max_value=5.0,
                                    step=0.5,
                                    value=3.0,
                                    format="%.1f"
                                )
                            
                            with col2:
                                st.write("")
                                st.write("")
                                if st.button("💾 평점 저장", type="primary"):
                                    try:
                                        # Firestore에 평점 저장
                                        success = firestore_manager.add_user_rating(
                                            user['uid'],
                                            selected_movie['movie_id'],
                                            rating
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
            
            elif input_method == "🎲 탐색":
                # 랜덤 영화 탐색
                st.markdown("인기 있는 영화들을 랜덤하게 탐색해보세요.")
                
                # 세션 상태 초기화
                if 'explored_movie_ids' not in st.session_state:
                    st.session_state.explored_movie_ids = set()
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    n_movies = st.slider("표시할 영화 개수", 5, 20, 10)
                with col2:
                    if st.button("🎲 새로운 영화 탐색", type="primary"):
                        # 새로운 영화들 가져오기
                        try:
                            random_movies, remaining_ids = get_random_popular_movies(
                                df_ratings, df_movies, n_movies, 
                                exclude_movie_ids=list(st.session_state.explored_movie_ids)
                            )
                            st.session_state.current_exploration = random_movies
                            st.session_state.explored_movie_ids.update(random_movies['movie_id'].tolist())
                        except Exception as e:
                            st.error(f"영화 탐색 중 오류가 발생했습니다: {e}")
                
                # 현재 탐색 중인 영화들 표시
                if 'current_exploration' in st.session_state and not st.session_state.current_exploration.empty:
                    st.markdown("### 🎬 탐색 중인 영화들")
                    st.markdown(f"*총 {len(st.session_state.current_exploration)}개의 영화*")
                    
                    for idx, (_, movie) in enumerate(st.session_state.current_exploration.iterrows(), 1):
                        st.markdown(f"#### {idx}. {movie.get('title', 'N/A')}")
                        display_movie_card(movie, show_plot=True)
                        
                        # 평점 입력
                        col_rating1, col_rating2, col_rating3 = st.columns([2, 1, 1])
                        
                        with col_rating1:
                            rating = st.slider(
                                f"평점을 선택하세요",
                                min_value=0.5,
                                max_value=5.0,
                                step=0.5,
                                value=3.0,
                                format="%.1f",
                                key=f"rating_{movie['movie_id']}"
                            )
                        
                        with col_rating2:
                            st.write("")
                            st.write("")
                            if st.button("💾 저장", key=f"save_{movie['movie_id']}"):
                                try:
                                    # Firestore에 평점 저장
                                    success = firestore_manager.add_user_rating(
                                        user['uid'],
                                        movie['movie_id'],
                                        rating
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
                        
                        st.markdown("---")
                else:
                    st.info("🎲 '새로운 영화 탐색' 버튼을 눌러서 영화를 탐색해보세요!")
            
            # 내 평점 목록
            st.markdown("---")
            st.subheader("📋 내 평점 목록")
            
            try:
                # 사용자의 평점 목록 조회
                user_ratings_df = firestore_manager.get_user_ratings(user['uid'])
                
                if not user_ratings_df.empty:
                    st.success(f"총 {len(user_ratings_df)}개의 평점이 있습니다.")
                    
                    # 평점 목록 표시
                    for idx, rating in user_ratings_df.head(10).iterrows():  # 최근 10개만 표시
                        movie_id = rating['movie_id']
                        rating_value = rating['rating']
                        
                        # 영화 정보 찾기
                        movie_info = df_movies[df_movies['movie_id'] == movie_id]
                        if not movie_info.empty:
                            movie = movie_info.iloc[0]
                            title = movie.get('title', 'N/A')
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"**{title}**")
                            with col2:
                                st.write(f"⭐ {rating_value}/5.0")
                            with col3:
                                if st.button("🗑️", key=f"delete_{rating.get('id', idx)}"):
                                    # 평점 삭제 기능 (구현 필요)
                                    st.info("평점 삭제 기능은 곧 추가될 예정입니다.")
                else:
                    st.info("아직 입력한 평점이 없습니다. 위에서 영화를 검색하여 평점을 입력해보세요!")
                    
            except Exception as e:
                st.error(f"평점 목록 조회 중 오류가 발생했습니다: {e}")
        
        except Exception as e:
            st.error(f"사용자 인증 오류: {e}")
    
    elif recommendation_type == "🎯 사용자 기반 추천":
        st.header("🎯 사용자 기반 추천")
        st.markdown("특정 사용자의 과거 평점을 분석하여 맞춤형 영화를 추천합니다.")
        
        # Firebase 사용 가능 여부 확인
        if not firebase_available:
            st.error("❌ Firebase가 설정되지 않았습니다.")
            st.info("사용자 기반 추천을 사용하려면 Firebase 설정이 필요합니다.")
            return
        
        # 로그인된 사용자 확인
        try:
            user = require_firebase_auth()
            if not user:
                st.error("로그인이 필요합니다.")
                st.info("사용자 기반 추천을 받으려면 로그인해주세요.")
                return
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 사용자 선택 옵션
                user_option = st.radio(
                    "추천 받을 사용자 선택",
                    ["👤 나 (현재 로그인된 사용자)", "👥 다른 사용자"],
                    help="추천을 받을 사용자를 선택하세요"
                )
                
                if user_option == "👤 나 (현재 로그인된 사용자)":
                    selected_user = user['uid']
                    st.info(f"현재 사용자: {user.get('display_name', 'User')}")
                else:
                    # 기존 데이터의 사용자 목록
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
                    try:
                        top_watched, recommendations = recommender.recommend_for_user(
                            selected_user, df_movies, n_recommendations
                        )
                    except KeyError as e:
                        if "나 (현재 로그인된 사용자)" in user_option:
                            st.warning("⚠️ 아직 학습되기 전입니다.")
                            st.info("""
                            **개인화 추천을 받으려면:**
                            1. 영화 평점을 더 많이 입력해주세요
                            2. 최소 10개 이상의 평점이 필요합니다
                            3. 평점 관리 탭에서 영화를 검색하여 평점을 입력해보세요
                            
                            **📚 학습 시스템 안내:**
                            - 10개 이상 평점을 입력하시면 추후 학습에 반영됩니다
                            - 학습 주기는 **1주일**입니다
                            - 매주 새로운 평점 데이터로 추천 모델이 업데이트됩니다
                            - 더 많은 평점을 입력할수록 더 정확한 추천을 받을 수 있습니다
                            """)
                            return
                        else:
                            st.error(f"추천 생성 중 오류가 발생했습니다: {e}")
                            return
                    except Exception as e:
                        error_msg = str(e)
                        if "나 (현재 로그인된 사용자)" in user_option and ("찾을 수 없습니다" in error_msg or "KeyError" in error_msg):
                            st.warning("⚠️ 아직 학습되기 전입니다.")
                            st.info("""
                            **개인화 추천을 받으려면:**
                            1. 영화 평점을 더 많이 입력해주세요
                            2. 최소 10개 이상의 평점이 필요합니다
                            3. 평점 관리 탭에서 영화를 검색하여 평점을 입력해보세요
                            
                            **📚 학습 시스템 안내:**
                            - 10개 이상 평점을 입력하시면 추후 학습에 반영됩니다
                            - 학습 주기는 **1주일**입니다
                            - 매주 새로운 평점 데이터로 추천 모델이 업데이트됩니다
                            - 더 많은 평점을 입력할수록 더 정확한 추천을 받을 수 있습니다
                            """)
                            return
                        else:
                            st.error(f"추천 생성 중 오류가 발생했습니다: {e}")
                            return
                
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
        
        except Exception as e:
            st.error(f"사용자 인증 오류: {e}")
    
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

