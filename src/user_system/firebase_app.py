"""
Firebase 기반 영화 추천 시스템 메인 앱
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
    }
    .stButton>button:hover {
        background-color: #E55A2B;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # 헤더
    st.markdown('<h1 class="main-header">🔥 Firebase 영화 추천 시스템</h1>', unsafe_allow_html=True)
    
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
                st.success(f"환영합니다, {user.get('display_name', 'User')}님!")
                
                # 메인 기능 탭
                tab1, tab2, tab3 = st.tabs(["🎬 영화 평점", "📊 추천 시스템", "ℹ️ 시스템 정보"])
                
                with tab1:
                    show_firebase_rating_main_page()
                
                with tab2:
                    st.subheader("🎯 개인화 추천 시스템")
                    st.info("""
                    **Firebase 기반 추천 시스템의 장점:**
                    
                    - **실시간 데이터**: 사용자 평점이 즉시 반영됩니다
                    - **확장성**: 수백만 사용자 지원
                    - **보안**: Firebase 보안 규칙으로 데이터 보호
                    - **오프라인**: 네트워크 없이도 작동
                    
                    추천 알고리즘은 기존 SVD 모델과 통합될 예정입니다.
                    """)
                
                with tab3:
                    st.subheader("🔥 Firebase 시스템 정보")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("""
                        **Firebase 서비스:**
                        - 🔐 Authentication (인증)
                        - 🗄️ Firestore (데이터베이스)
                        - 🔒 Security Rules (보안)
                        - 📊 Analytics (분석)
                        """)
                    
                    with col2:
                        st.markdown("""
                        **데이터 구조:**
                        - `users/` - 사용자 정보
                        - `user_ratings/` - 사용자 평점
                        - `movie_metadata/` - 영화 정보
                        """)
                    
                    # Firebase 상태 표시
                    st.markdown("### 📊 시스템 상태")
                    st.success("✅ Firebase 연결 정상")
                    st.success("✅ Firestore 데이터베이스 정상")
                    st.success("✅ 사용자 인증 정상")
        
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
