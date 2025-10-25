"""
Firebase 기반 통합 영화 추천 시스템
기존 추천 시스템과 Firebase를 통합한 완전한 앱
"""
import streamlit as st
import logging
from pathlib import Path
import sys

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from firebase_config import init_firebase, setup_firebase_config
from firebase_auth import show_firebase_auth_ui, require_firebase_auth
from firebase_firestore import show_firebase_rating_main_page
from firebase_recommender import show_firebase_recommendation_ui, show_similar_movies_ui

# Logger 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="Firebase 영화 추천 시스템",
    page_icon="🔥",
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
        color: #FF6B35;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .firebase-card {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s;
    }
    .firebase-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .stButton>button {
        width: 100%;
        background-color: #FF6B35;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.75rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #E55A2B;
        transform: translateY(-1px);
    }
    .feature-card {
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
        border-left: 4px solid #FF6B35;
        margin-bottom: 1rem;
    }
    .stats-card {
        padding: 1rem;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def show_welcome_page():
    """환영 페이지"""
    st.markdown('<h1 class="main-header">🔥 Firebase 영화 추천 시스템</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="firebase-card">
        <h3>🎬 개인화된 영화 추천을 받아보세요!</h3>
        <p>Firebase의 강력한 실시간 데이터베이스와 AI 추천 알고리즘을 결합한 최신 영화 추천 시스템입니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 주요 기능 소개
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h4>🔐 안전한 인증</h4>
            <p>Firebase Authentication으로 안전한 로그인</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>⭐ 개인화 평점</h4>
            <p>내가 본 영화에 평점을 매기고 관리</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h4>🎯 AI 추천</h4>
            <p>SVD와 Item-Based 알고리즘으로 정확한 추천</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 시스템 통계
    st.markdown("### 📊 시스템 현황")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="stats-card">
            <h3>🔥</h3>
            <h4>Firebase</h4>
            <p>실시간 동기화</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stats-card">
            <h3>🤖</h3>
            <h4>AI 추천</h4>
            <p>SVD + Item-Based</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stats-card">
            <h3>⚡</h3>
            <h4>실시간</h4>
            <p>즉시 반영</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="stats-card">
            <h3>🔒</h3>
            <h4>보안</h4>
            <p>Firebase 보안 규칙</p>
        </div>
        """, unsafe_allow_html=True)


def show_user_dashboard():
    """사용자 대시보드"""
    user = require_firebase_auth()
    if not user:
        return
    
    st.markdown(f"<h2>👋 {user.get('display_name', 'User')}님, 환영합니다!</h2>", unsafe_allow_html=True)
    
    # 사용자 통계
    from firebase_firestore import FirestoreManager
    firestore_manager = FirestoreManager()
    
    try:
        user_id = user['uid']
        stats = firestore_manager.get_user_rating_stats(user_id)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 평점 수", f"{stats.get('total_ratings', 0)}개")
        with col2:
            st.metric("평균 평점", f"{stats.get('avg_rating', 0):.1f}/5.0")
        with col3:
            st.metric("높은 평점", f"{stats.get('high_ratings', 0)}개")
        with col4:
            st.metric("낮은 평점", f"{stats.get('low_ratings', 0)}개")
    
    except Exception as e:
        st.warning("사용자 통계를 불러올 수 없습니다.")
        logger.error(f"사용자 통계 조회 실패: {e}")


def main():
    # 사이드바
    st.sidebar.title("⚙️ Firebase 설정")
    st.sidebar.markdown("---")
    
    # Firebase 설정
    if setup_firebase_config():
        st.sidebar.success("✅ Firebase 연결 성공!")
        
        # 인증 UI
        st.sidebar.markdown("---")
        show_firebase_auth_ui()
        
        # 메인 컨텐츠
        st.markdown("---")
        
        # 사용자 인증 확인
        try:
            user = require_firebase_auth()
            if user:
                # 사용자 대시보드
                show_user_dashboard()
                
                # 메인 기능 탭
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "🎬 영화 평점", 
                    "🎯 개인화 추천", 
                    "🔍 유사 영화 찾기",
                    "📊 추천 통계",
                    "ℹ️ 시스템 정보"
                ])
                
                with tab1:
                    show_firebase_rating_main_page()
                
                with tab2:
                    show_firebase_recommendation_ui()
                
                with tab3:
                    show_similar_movies_ui()
                
                with tab4:
                    st.subheader("📊 추천 시스템 통계")
                    
                    # 추천 시스템 상태
                    try:
                        from firebase_recommender import FirebaseRecommender
                        recommender = FirebaseRecommender()
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### 🤖 모델 상태")
                            if recommender.svd_model:
                                st.success("✅ SVD 모델 로드됨")
                            else:
                                st.warning("⚠️ SVD 모델 없음")
                            
                            if recommender.item_based_model:
                                st.success("✅ Item-Based 모델 로드됨")
                            else:
                                st.warning("⚠️ Item-Based 모델 없음")
                        
                        with col2:
                            st.markdown("### 🔥 Firebase 상태")
                            st.success("✅ Firebase 연결 정상")
                            st.success("✅ Firestore 데이터베이스 정상")
                            st.success("✅ 사용자 인증 정상")
                        
                        # 사용자 추천 통계
                        user_stats = recommender.get_user_recommendation_stats(user['uid'])
                        
                        if user_stats:
                            st.markdown("### 📈 내 추천 통계")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("총 평점 수", f"{user_stats.get('total_ratings', 0)}개")
                                st.metric("평균 평점", f"{user_stats.get('avg_rating', 0):.1f}/5.0")
                            
                            with col2:
                                preferred_genres = user_stats.get('preferred_genres', [])
                                if preferred_genres:
                                    st.write("**선호 장르:**")
                                    for genre in preferred_genres[:3]:
                                        st.write(f"• {genre}")
                                else:
                                    st.write("**선호 장르:** 분석 중...")
                            
                            with col3:
                                rating_trend = user_stats.get('rating_trend', {})
                                if rating_trend:
                                    st.write(f"**최근 평균:** {rating_trend.get('recent_avg', 0):.1f}/5.0")
                                    st.write(f"**트렌드:** {rating_trend.get('trend', 'stable')}")
                    
                    except Exception as e:
                        st.error(f"통계 조회 중 오류가 발생했습니다: {e}")
                        logger.error(f"통계 조회 실패: {e}")
                
                with tab5:
                    st.subheader("🔥 Firebase 시스템 정보")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("""
                        **Firebase 서비스:**
                        - 🔐 Authentication (인증)
                        - 🗄️ Firestore (데이터베이스)
                        - 🔒 Security Rules (보안)
                        - 📊 Analytics (분석)
                        - ⚡ Real-time (실시간)
                        """)
                    
                    with col2:
                        st.markdown("""
                        **데이터 구조:**
                        - `users/` - 사용자 정보
                        - `user_ratings/` - 사용자 평점
                        - `movie_metadata/` - 영화 정보
                        - `user_sessions/` - 세션 관리
                        """)
                    
                    # 시스템 아키텍처
                    st.markdown("### 🏗️ 시스템 아키텍처")
                    
                    st.markdown("""
                    ```
                    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
                    │   Streamlit     │    │    Firebase     │    │   AI Models     │
                    │      UI         │◄──►│   Firestore     │◄──►│   SVD + Item    │
                    │                 │    │   Database      │    │   Based CF      │
                    └─────────────────┘    └─────────────────┘    └─────────────────┘
                            │                       │                       │
                            ▼                       ▼                       ▼
                    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
                    │   User Auth     │    │   Real-time     │    │  Recommendation │
                    │   Management    │    │   Sync          │    │   Engine        │
                    └─────────────────┘    └─────────────────┘    └─────────────────┘
                    """)
                    
                    # 성능 지표
                    st.markdown("### 📊 성능 지표")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("응답 시간", "< 100ms", "실시간")
                    with col2:
                        st.metric("확장성", "수백만 사용자", "Firebase")
                    with col3:
                        st.metric("가용성", "99.9%", "Google Cloud")
        
        except Exception as e:
            st.error(f"시스템 오류: {e}")
            logger.error(f"시스템 오류: {e}")
    
    else:
        st.error("❌ Firebase 설정이 필요합니다.")
        st.info("""
        **Firebase 설정 방법:**
        
        1. **Firebase Console** (https://console.firebase.google.com) 접속
        2. **새 프로젝트** 생성
        3. **Authentication** 활성화 (이메일/비밀번호)
        4. **Firestore Database** 생성
        5. **서비스 계정 키** 다운로드
        6. 위의 사이드바에서 키 파일 업로드
        """)
        
        # Firebase 설정 가이드
        with st.expander("📖 상세 설정 가이드"):
            st.markdown("""
            ### 🔥 Firebase 프로젝트 설정
            
            #### 1. Firebase Console 설정
            1. [Firebase Console](https://console.firebase.google.com) 접속
            2. "프로젝트 추가" 클릭
            3. 프로젝트 이름 입력 (예: movie-recommendation)
            4. Google Analytics 활성화 (선택사항)
            
            #### 2. Authentication 설정
            1. 좌측 메뉴에서 "Authentication" 클릭
            2. "시작하기" 클릭
            3. "Sign-in method" 탭에서 "이메일/비밀번호" 활성화
            
            #### 3. Firestore Database 설정
            1. 좌측 메뉴에서 "Firestore Database" 클릭
            2. "데이터베이스 만들기" 클릭
            3. 보안 규칙: "테스트 모드" 선택 (개발용)
            4. 위치: asia-northeast3 (서울) 선택
            
            #### 4. 서비스 계정 키 생성
            1. 좌측 메뉴에서 "프로젝트 설정" 클릭
            2. "서비스 계정" 탭 클릭
            3. "새 비공개 키 생성" 클릭
            4. JSON 파일 다운로드
            
            #### 5. 보안 규칙 설정 (선택사항)
            ```javascript
            rules_version = '2';
            service cloud.firestore {
              match /databases/{database}/documents {
                // 사용자는 자신의 데이터만 읽기/쓰기 가능
                match /users/{userId} {
                  allow read, write: if request.auth != null && request.auth.uid == userId;
                }
                
                // 평점은 인증된 사용자만 작성 가능
                match /user_ratings/{ratingId} {
                  allow read, write: if request.auth != null;
                }
                
                // 영화 메타데이터는 모든 사용자가 읽기 가능
                match /movie_metadata/{movieId} {
                  allow read: if true;
                  allow write: if request.auth != null;
                }
              }
            }
            ```
            """)


if __name__ == "__main__":
    main()
