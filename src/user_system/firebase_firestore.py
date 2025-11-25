"""
Firebase Firestore 기반 데이터 관리
사용자 평점, 영화 메타데이터 관리
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from .firebase_auth import get_current_user_uid
from .firebase_config import FirestoreCollections, get_firebase_manager

# Logger 설정
logger = logging.getLogger(__name__)


class FirestoreManager:
    """Firestore 데이터 관리 클래스"""

    def __init__(self):
        self.firebase_manager = get_firebase_manager()
        self.db = None

    def _get_firestore(self):
        """Firestore 클라이언트 가져오기"""
        if not self.firebase_manager.initialized:
            raise ValueError("Firebase가 초기화되지 않았습니다.")

        if self.db is None:
            self.db = self.firebase_manager.get_firestore()

        return self.db

    def add_user_rating(self, user_id: str, movie_id: str, rating: float) -> bool:
        """사용자 평점 추가/업데이트"""
        # 평점 범위 검증
        if not (0.5 <= rating <= 5.0):
            raise ValueError("평점은 0.5 ~ 5.0 사이여야 합니다.")

        try:
            db = self._get_firestore()

            # 평점 데이터
            rating_data = {
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": rating,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # 사용자별 영화 평점 문서 ID 생성 (user_id + movie_id)
            doc_id = f"{user_id}_{movie_id}"

            # 평점 저장 (덮어쓰기)
            db.collection(FirestoreCollections.USER_RATINGS).document(doc_id).set(rating_data)

            logger.info(f"✅ 평점 저장 완료: 사용자 {user_id}, 영화 {movie_id}, 평점 {rating}")
            return True

        except Exception as e:
            logger.error(f"❌ 평점 저장 실패: {e}")
            return False

    def get_user_ratings(self, user_id: str) -> pd.DataFrame:
        """사용자 평점 조회"""
        try:
            db = self._get_firestore()

            # 사용자 평점 쿼리
            ratings_query = db.collection(FirestoreCollections.USER_RATINGS).where("user_id", "==", user_id)
            ratings = list(ratings_query.stream())

            if not ratings:
                return pd.DataFrame()

            # 데이터프레임으로 변환
            ratings_data = []
            for rating in ratings:
                rating_dict = rating.to_dict()
                rating_dict["id"] = rating.id
                ratings_data.append(rating_dict)

            return pd.DataFrame(ratings_data)

        except Exception as e:
            logger.error(f"사용자 평점 조회 실패: {e}")
            return pd.DataFrame()

    def get_user_rating_stats(self, user_id: str) -> Dict[str, Any]:
        """사용자 평점 통계"""
        try:
            db = self._get_firestore()

            # 사용자 평점 쿼리
            ratings_query = db.collection(FirestoreCollections.USER_RATINGS).where("user_id", "==", user_id)
            ratings = list(ratings_query.stream())

            if not ratings:
                return {
                    "total_ratings": 0,
                    "avg_rating": 0.0,
                    "min_rating": 0.0,
                    "max_rating": 0.0,
                    "high_ratings": 0,
                    "low_ratings": 0,
                }

            # 통계 계산
            ratings_list = [rating.to_dict()["rating"] for rating in ratings]

            stats = {
                "total_ratings": len(ratings_list),
                "avg_rating": sum(ratings_list) / len(ratings_list),
                "min_rating": min(ratings_list),
                "max_rating": max(ratings_list),
                "high_ratings": len([r for r in ratings_list if r >= 4.0]),
                "low_ratings": len([r for r in ratings_list if r <= 2.0]),
            }

            return stats

        except Exception as e:
            logger.error(f"평점 통계 조회 실패: {e}")
            return {}

    def get_movie_ratings(self, movie_id: str) -> pd.DataFrame:
        """영화 평점 조회"""
        try:
            db = self._get_firestore()

            # 영화 평점 쿼리
            ratings_query = db.collection(FirestoreCollections.USER_RATINGS).where("movie_id", "==", movie_id)
            ratings = list(ratings_query.stream())

            if not ratings:
                return pd.DataFrame()

            # 데이터프레임으로 변환
            ratings_data = []
            for rating in ratings:
                rating_dict = rating.to_dict()
                rating_dict["id"] = rating.id
                ratings_data.append(rating_dict)

            return pd.DataFrame(ratings_data)

        except Exception as e:
            logger.error(f"영화 평점 조회 실패: {e}")
            return pd.DataFrame()

    def get_rating_matrix(self) -> pd.DataFrame:
        """평점 매트릭스 조회 (추천 시스템용)"""
        try:
            db = self._get_firestore()

            # 모든 평점 조회
            ratings_query = db.collection(FirestoreCollections.USER_RATINGS)
            ratings = list(ratings_query.stream())

            if not ratings:
                return pd.DataFrame()

            # 데이터프레임으로 변환
            ratings_data = []
            for rating in ratings:
                rating_dict = rating.to_dict()
                ratings_data.append(
                    {
                        "user_id": rating_dict["user_id"],
                        "movie_id": rating_dict["movie_id"],
                        "rating": rating_dict["rating"],
                    }
                )

            return pd.DataFrame(ratings_data)

        except Exception as e:
            logger.error(f"평점 매트릭스 조회 실패: {e}")
            return pd.DataFrame()

    def add_movie_metadata(self, movie_data: Dict[str, Any]) -> bool:
        """영화 메타데이터 추가"""
        try:
            db = self._get_firestore()

            # 영화 메타데이터 저장
            movie_data["created_at"] = datetime.now().isoformat()
            db.collection(FirestoreCollections.MOVIE_METADATA).document(movie_data["movie_id"]).set(movie_data)

            logger.info(f"✅ 영화 메타데이터 저장 완료: {movie_data['movie_id']}")
            return True

        except Exception as e:
            logger.error(f"❌ 영화 메타데이터 저장 실패: {e}")
            return False

    def get_movie_metadata(self, movie_id: str) -> Optional[Dict[str, Any]]:
        """영화 메타데이터 조회"""
        try:
            db = self._get_firestore()

            movie_doc = db.collection(FirestoreCollections.MOVIE_METADATA).document(movie_id).get()

            if movie_doc.exists:
                return movie_doc.to_dict()
            else:
                return None

        except Exception as e:
            logger.error(f"영화 메타데이터 조회 실패: {e}")
            return None

    def search_movies(self, query: str, limit: int = 10) -> pd.DataFrame:
        """영화 검색"""
        try:
            db = self._get_firestore()

            # 제목으로 검색 (대소문자 구분 없음)
            movies_query = db.collection(FirestoreCollections.MOVIE_METADATA).limit(limit)
            movies = list(movies_query.stream())

            # 클라이언트 사이드에서 필터링 (Firestore의 제한적 검색 기능)
            filtered_movies = []
            for movie in movies:
                movie_dict = movie.to_dict()
                if query.lower() in movie_dict.get("title", "").lower():
                    movie_dict["id"] = movie.id
                    filtered_movies.append(movie_dict)

            return pd.DataFrame(filtered_movies)

        except Exception as e:
            logger.error(f"영화 검색 실패: {e}")
            return pd.DataFrame()

    def get_all_movies(self, limit: int = 100) -> pd.DataFrame:
        """모든 영화 조회"""
        try:
            db = self._get_firestore()

            movies_query = db.collection(FirestoreCollections.MOVIE_METADATA).limit(limit)
            movies = list(movies_query.stream())

            if not movies:
                return pd.DataFrame()

            # 데이터프레임으로 변환
            movies_data = []
            for movie in movies:
                movie_dict = movie.to_dict()
                movie_dict["id"] = movie.id
                movies_data.append(movie_dict)

            return pd.DataFrame(movies_data)

        except Exception as e:
            logger.error(f"영화 목록 조회 실패: {e}")
            return pd.DataFrame()

    def delete_user_rating(self, user_id: str, movie_id: str) -> bool:
        """사용자 평점 삭제"""
        try:
            db = self._get_firestore()

            # 평점 문서 ID
            doc_id = f"{user_id}_{movie_id}"

            # 평점 삭제
            db.collection(FirestoreCollections.USER_RATINGS).document(doc_id).delete()

            logger.info(f"✅ 평점 삭제 완료: 사용자 {user_id}, 영화 {movie_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 평점 삭제 실패: {e}")
            return False

    def get_all_user_ratings(self) -> pd.DataFrame:
        """모든 사용자의 평점 데이터 조회 (모델 학습용)"""
        try:
            db = self._get_firestore()

            # 모든 평점 데이터 조회
            ratings_ref = db.collection(FirestoreCollections.USER_RATINGS)
            docs = ratings_ref.stream()

            ratings_data = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                ratings_data.append(data)

            if not ratings_data:
                return pd.DataFrame()

            # DataFrame으로 변환
            df = pd.DataFrame(ratings_data)

            # 데이터 타입 변환
            if "rating" in df.columns:
                df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
            if "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

            # 필요한 컬럼만 선택 (기존 데이터와 호환)
            required_columns = ["user_id", "movie_id", "rating"]
            if all(col in df.columns for col in required_columns):
                df = df[required_columns]
            else:
                logger.warning("필수 컬럼이 없습니다. 전체 데이터를 반환합니다.")

            return df

        except Exception as e:
            logger.error(f"모든 사용자 평점 조회 중 오류: {e}")
            return pd.DataFrame()

    def get_user_interaction_stats(self) -> Dict[str, Any]:
        """사용자 상호작용 통계 조회"""
        try:
            db = self._get_firestore()

            # 전체 평점 수
            ratings_ref = db.collection(FirestoreCollections.USER_RATINGS)
            total_ratings = len(list(ratings_ref.stream()))

            # 고유 사용자 수
            users_ref = db.collection(FirestoreCollections.USER_RATINGS)
            docs = users_ref.stream()
            unique_users = set()
            for doc in docs:
                data = doc.to_dict()
                if "user_id" in data:
                    unique_users.add(data["user_id"])

            # 고유 영화 수
            unique_movies = set()
            docs = users_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                if "movie_id" in data:
                    unique_movies.add(data["movie_id"])

            return {
                "total_ratings": total_ratings,
                "unique_users": len(unique_users),
                "unique_movies": len(unique_movies),
                "avg_ratings_per_user": total_ratings / len(unique_users) if unique_users else 0,
            }

        except Exception as e:
            logger.error(f"사용자 상호작용 통계 조회 중 오류: {e}")
            return {"total_ratings": 0, "unique_users": 0, "unique_movies": 0, "avg_ratings_per_user": 0}


class RatingUI:
    """Firebase 기반 영화 평점 UI 클래스"""

    def __init__(self):
        self.firestore_manager = FirestoreManager()

    def show_rating_form(self, movie_data: Dict[str, Any]) -> bool:
        """영화 평점 폼 표시"""
        user_id = get_current_user_uid()
        if not user_id:
            st.error("로그인이 필요합니다.")
            return False

        movie_id = movie_data.get("movie_id")
        movie_title = movie_data.get("title", "Unknown")

        st.subheader(f"⭐ {movie_title} 평점하기")

        # 현재 평점 확인
        try:
            user_ratings = self.firestore_manager.get_user_ratings(user_id)
            current_rating = None

            if not user_ratings.empty:
                user_movie_rating = user_ratings[user_ratings["movie_id"] == movie_id]
                if not user_movie_rating.empty:
                    current_rating = user_movie_rating.iloc[0]["rating"]
        except Exception as e:
            logger.error(f"현재 평점 조회 실패: {e}")
            current_rating = None

        # 평점 입력 폼
        with st.form(f"rating_form_{movie_id}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                if current_rating:
                    st.info(f"현재 평점: {current_rating}/5.0")
                    rating = st.slider(
                        "평점을 선택하세요", min_value=0.5, max_value=5.0, step=0.5, value=current_rating, format="%.1f"
                    )
                else:
                    rating = st.slider(
                        "평점을 선택하세요", min_value=0.5, max_value=5.0, step=0.5, value=3.0, format="%.1f"
                    )

            with col2:
                st.write("")  # 공간
                st.write("")  # 공간
                submit_rating = st.form_submit_button("평점 저장", use_container_width=True)

            if submit_rating:
                try:
                    success = self.firestore_manager.add_user_rating(user_id, movie_id, rating)

                    if success:
                        st.success(f"평점이 저장되었습니다! ({rating}/5.0)")
                        st.rerun()
                    else:
                        st.error("평점 저장에 실패했습니다.")
                except Exception as e:
                    logger.error(f"평점 저장 실패: {e}")
                    st.error("평점 저장 중 오류가 발생했습니다.")

        return True

    def show_user_ratings(self):
        """사용자 평점 목록 표시"""
        user_id = get_current_user_uid()
        if not user_id:
            st.error("로그인이 필요합니다.")
            return

        st.subheader("📝 내가 평가한 영화들")

        try:
            user_ratings = self.firestore_manager.get_user_ratings(user_id)
            stats = self.firestore_manager.get_user_rating_stats(user_id)

            if user_ratings.empty:
                st.info("아직 평가한 영화가 없습니다.")
                return

            # 통계 표시
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 평점 수", f"{stats.get('total_ratings', 0)}개")
            with col2:
                st.metric("평균 평점", f"{stats.get('avg_rating', 0):.1f}/5.0")
            with col3:
                st.metric("높은 평점 (4.0+)", f"{stats.get('high_ratings', 0)}개")
            with col4:
                st.metric("낮은 평점 (2.0-)", f"{stats.get('low_ratings', 0)}개")

            st.markdown("---")

            # 평점 목록 표시
            for _idx, row in user_ratings.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.write(f"**영화 ID:** {row['movie_id']}")
                        st.write(f"**평점:** {row['rating']}/5.0")
                        st.write(f"**평점일:** {row['created_at']}")

                    with col2:
                        st.metric("내 평점", f"{row['rating']}/5.0")

                    with col3:
                        if st.button("삭제", key=f"delete_{row['id']}", type="secondary"):
                            if self.firestore_manager.delete_user_rating(user_id, row["movie_id"]):
                                st.success("평점이 삭제되었습니다!")
                                st.rerun()
                            else:
                                st.error("평점 삭제에 실패했습니다.")

        except Exception as e:
            logger.error(f"사용자 평점 조회 실패: {e}")
            st.error("평점 목록을 불러오는 중 오류가 발생했습니다.")

    def show_movie_search_and_rate(self):
        """영화 검색 및 평점 페이지"""
        user_id = get_current_user_uid()
        if not user_id:
            st.error("로그인이 필요합니다.")
            return

        st.subheader("🔍 영화 검색 및 평점")

        # 영화 검색
        search_query = st.text_input("영화 제목을 검색하세요", placeholder="예: 타이타닉, 어벤져스, 기생충...")

        if search_query and search_query.strip():
            try:
                search_results = self.firestore_manager.search_movies(search_query, limit=10)

                if not search_results.empty:
                    st.write(f"**{len(search_results)}개**의 영화를 찾았습니다.")

                    # 영화 목록 표시
                    for _idx, movie in search_results.iterrows():
                        with st.expander(f"{movie['title']} ({movie.get('year', 'N/A')})"):
                            col1, col2 = st.columns([2, 1])

                            with col1:
                                st.write(f"**장르:** {movie.get('genre', 'N/A')}")
                                st.write(f"**국가:** {movie.get('country', 'N/A')}")
                                st.write(f"**러닝타임:** {movie.get('runtime', 'N/A')}분")
                                if pd.notna(movie.get("plot")):
                                    st.write(f"**줄거리:** {movie['plot'][:200]}...")

                            with col2:
                                if st.button("평점하기", key=f"rate_{movie['movie_id']}"):
                                    st.session_state.selected_movie = movie.to_dict()
                                    st.rerun()
                else:
                    st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
            except Exception as e:
                logger.error(f"영화 검색 실패: {e}")
                st.error("영화 검색 중 오류가 발생했습니다.")

        # 선택된 영화 평점 폼
        if "selected_movie" in st.session_state:
            st.markdown("---")
            self.show_rating_form(st.session_state.selected_movie)

            if st.button("평점 취소"):
                del st.session_state.selected_movie
                st.rerun()


def show_firebase_rating_main_page():
    """Firebase 기반 평점 메인 페이지"""
    rating_ui = RatingUI()

    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["🔍 영화 검색 & 평점", "📝 내 평점 목록", "ℹ️ 도움말"])

    with tab1:
        rating_ui.show_movie_search_and_rate()

    with tab2:
        rating_ui.show_user_ratings()

    with tab3:
        st.markdown("""
        ### 📖 Firebase 평점 시스템 사용법
        
        #### 🔍 영화 검색 & 평점
        1. 영화 제목을 검색합니다
        2. 원하는 영화를 선택합니다
        3. 0.5~5.0 사이의 평점을 선택합니다
        4. '평점 저장' 버튼을 클릭합니다
        
        #### 📝 내 평점 목록
        - 내가 평가한 모든 영화를 확인할 수 있습니다
        - 평점 통계를 한눈에 볼 수 있습니다
        - 평점 삭제도 가능합니다
        
        #### 💡 Firebase의 장점
        - **실시간 동기화**: 평점이 즉시 저장됩니다
        - **확장성**: 수백만 사용자 지원
        - **보안**: Firebase 보안 규칙으로 데이터 보호
        - **오프라인**: 네트워크 없이도 작동
        """)


if __name__ == "__main__":
    st.title("Firebase 영화 평점 시스템")
    show_firebase_rating_main_page()
