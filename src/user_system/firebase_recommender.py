"""
Firebase 기반 개인화 추천 시스템
기존 SVD 모델과 Firestore 데이터를 통합
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from firebase_auth import get_current_user_uid, require_firebase_auth
from firebase_firestore import FirestoreManager

# 기존 추천 시스템 import
try:
    from modeling.models.item_based import ItemBasedRecommender
    from modeling.models.svd import SVDRecommenderPipeline
except ImportError:
    st.error("기존 추천 시스템 모델을 찾을 수 없습니다.")
    st.stop()

# Logger 설정
logger = logging.getLogger(__name__)


class FirebaseRecommender:
    """Firebase 기반 개인화 추천 시스템"""

    def __init__(self):
        self.firestore_manager = FirestoreManager()
        self.svd_model = None
        self.item_based_model = None
        self.movie_metadata = None

        # 모델 로드
        self._load_models()

    def _load_models(self):
        """기존 학습된 모델들 로드"""
        try:
            # SVD 모델 로드
            svd_path = project_root / "modeling" / "models" / "pkls" / "trained_svd_pipeline.pkl"
            if svd_path.exists():
                self.svd_model = SVDRecommenderPipeline.load_model(str(svd_path))
                logger.info("✅ SVD 모델 로드 완료")
            else:
                logger.warning("⚠️ SVD 모델 파일을 찾을 수 없습니다.")

            # Item-Based 모델 로드
            item_based_path = project_root / "modeling" / "models" / "pkls" / "trained_item_based.pkl"
            if item_based_path.exists():
                self.item_based_model = ItemBasedRecommender.load(str(item_based_path))
                logger.info("✅ Item-Based 모델 로드 완료")
            else:
                logger.warning("⚠️ Item-Based 모델 파일을 찾을 수 없습니다.")

        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")

    def _get_user_ratings_from_firestore(self, user_id: str) -> pd.DataFrame:
        """Firestore에서 사용자 평점 조회"""
        try:
            user_ratings = self.firestore_manager.get_user_ratings(user_id)
            return user_ratings
        except Exception as e:
            logger.error(f"사용자 평점 조회 실패: {e}")
            return pd.DataFrame()

    def _get_movie_metadata_from_firestore(self) -> pd.DataFrame:
        """Firestore에서 영화 메타데이터 조회"""
        try:
            if self.movie_metadata is None:
                self.movie_metadata = self.firestore_manager.get_all_movies(limit=1000)
            return self.movie_metadata
        except Exception as e:
            logger.error(f"영화 메타데이터 조회 실패: {e}")
            return pd.DataFrame()

    def _create_rating_matrix_from_firestore(self) -> pd.DataFrame:
        """Firestore 데이터로부터 평점 매트릭스 생성"""
        try:
            # Firestore에서 모든 평점 조회
            all_ratings = self.firestore_manager.get_rating_matrix()

            if all_ratings.empty:
                logger.warning("Firestore에 평점 데이터가 없습니다.")
                return pd.DataFrame()

            # 기존 SVD 모델의 데이터와 병합
            if self.svd_model and hasattr(self.svd_model, "df_filtered"):
                # 기존 데이터와 Firestore 데이터 병합
                existing_ratings = self.svd_model.df_filtered
                combined_ratings = pd.concat([existing_ratings, all_ratings], ignore_index=True)

                # 중복 제거 (같은 사용자-영화 조합)
                combined_ratings = combined_ratings.drop_duplicates(subset=["user_id", "movie_id"])

                return combined_ratings
            else:
                return all_ratings

        except Exception as e:
            logger.error(f"평점 매트릭스 생성 실패: {e}")
            return pd.DataFrame()

    def recommend_for_user(self, user_id: str, n_recommendations: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """사용자에게 영화 추천"""
        try:
            # 사용자 평점 조회
            user_ratings = self._get_user_ratings_from_firestore(user_id)

            if user_ratings.empty:
                # Cold Start: 인기 영화 추천
                return self._get_popular_movies(n_recommendations), pd.DataFrame()

            # 평점 수가 적으면 (5개 미만) 인기 영화 추천
            if len(user_ratings) < 5:
                return self._get_popular_movies(n_recommendations), user_ratings

            # SVD 모델이 있으면 사용
            if self.svd_model:
                try:
                    # Firestore 데이터를 SVD 모델에 통합
                    firestore_ratings = self._create_rating_matrix_from_firestore()

                    if not firestore_ratings.empty:
                        # 임시로 사용자 ID를 기존 모델 형식에 맞게 변환
                        # 실제로는 모델을 재학습하거나 온라인 학습이 필요
                        return self._recommend_with_svd(user_id, firestore_ratings, n_recommendations)
                except Exception as e:
                    logger.warning(f"SVD 추천 실패, 대체 방법 사용: {e}")

            # SVD 모델이 없거나 실패하면 Item-Based 추천
            if self.item_based_model:
                return self._recommend_with_item_based(user_ratings, n_recommendations)

            # 모든 모델이 실패하면 인기 영화 추천
            return self._get_popular_movies(n_recommendations), user_ratings

        except Exception as e:
            logger.error(f"추천 생성 실패: {e}")
            return self._get_popular_movies(n_recommendations), pd.DataFrame()

    def _recommend_with_svd(
        self, user_id: str, ratings_data: pd.DataFrame, n: int
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """SVD 모델을 사용한 추천"""
        try:
            # 영화 메타데이터 조회
            movie_metadata = self._get_movie_metadata_from_firestore()

            if movie_metadata.empty:
                return self._get_popular_movies(n), pd.DataFrame()

            # SVD 모델로 추천 (기존 사용자 ID가 있는 경우)
            if user_id in ratings_data["user_id"].values:
                top_watched, recommendations = self.svd_model.recommend_for_user(user_id, movie_metadata, n)
                return top_watched, recommendations
            else:
                # 새 사용자는 인기 영화 추천
                return self._get_popular_movies(n), pd.DataFrame()

        except Exception as e:
            logger.error(f"SVD 추천 실패: {e}")
            return self._get_popular_movies(n), pd.DataFrame()

    def _recommend_with_item_based(self, user_ratings: pd.DataFrame, n: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Item-Based 모델을 사용한 추천"""
        try:
            # 사용자가 높게 평가한 영화들
            high_rated_movies = user_ratings[user_ratings["rating"] >= 4.0]

            if high_rated_movies.empty:
                return self._get_popular_movies(n), user_ratings

            # 가장 높게 평가한 영화로부터 유사 영화 추천
            best_movie_id = high_rated_movies.loc[high_rated_movies["rating"].idxmax(), "movie_id"]

            # Item-Based 모델로 유사 영화 찾기
            similar_movies = self.item_based_model.recommend(movie_id=best_movie_id, top_n=n, return_scores=True)

            if similar_movies is not None and not similar_movies.empty:
                # 영화 메타데이터와 병합
                movie_metadata = self._get_movie_metadata_from_firestore()
                if not movie_metadata.empty:
                    recommendations = pd.merge(similar_movies, movie_metadata, on="movie_id", how="left")
                    return user_ratings, recommendations

            return user_ratings, self._get_popular_movies(n)

        except Exception as e:
            logger.error(f"Item-Based 추천 실패: {e}")
            return user_ratings, self._get_popular_movies(n)

    def _get_popular_movies(self, n: int) -> pd.DataFrame:
        """인기 영화 추천 (Cold Start 대응)"""
        try:
            movie_metadata = self._get_movie_metadata_from_firestore()

            if movie_metadata.empty:
                return pd.DataFrame()

            # 인기도와 평점 기준으로 정렬
            if "popularity" in movie_metadata.columns and "avg_score" in movie_metadata.columns:
                popular_movies = movie_metadata.sort_values(["popularity", "avg_score"], ascending=[False, False]).head(
                    n
                )
            else:
                # 기본 정렬
                popular_movies = movie_metadata.head(n)

            return popular_movies

        except Exception as e:
            logger.error(f"인기 영화 조회 실패: {e}")
            return pd.DataFrame()

    def find_similar_movies(self, movie_id: str, n: int = 10) -> pd.DataFrame:
        """유사 영화 찾기"""
        try:
            if self.item_based_model:
                similar_movies = self.item_based_model.recommend(movie_id=movie_id, top_n=n, return_scores=True)

                if similar_movies is not None and not similar_movies.empty:
                    # 영화 메타데이터와 병합
                    movie_metadata = self._get_movie_metadata_from_firestore()
                    if not movie_metadata.empty:
                        result = pd.merge(similar_movies, movie_metadata, on="movie_id", how="left")
                        return result

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"유사 영화 찾기 실패: {e}")
            return pd.DataFrame()

    def get_user_recommendation_stats(self, user_id: str) -> Dict[str, Any]:
        """사용자 추천 통계"""
        try:
            user_ratings = self._get_user_ratings_from_firestore(user_id)
            stats = self.firestore_manager.get_user_rating_stats(user_id)

            return {
                "total_ratings": stats.get("total_ratings", 0),
                "avg_rating": stats.get("avg_rating", 0.0),
                "rating_distribution": user_ratings["rating"].value_counts().to_dict()
                if not user_ratings.empty
                else {},
                "preferred_genres": self._get_user_preferred_genres(user_ratings),
                "rating_trend": self._get_rating_trend(user_ratings),
            }

        except Exception as e:
            logger.error(f"추천 통계 조회 실패: {e}")
            return {}

    def _get_user_preferred_genres(self, user_ratings: pd.DataFrame) -> List[str]:
        """사용자 선호 장르 분석"""
        try:
            if user_ratings.empty:
                return []

            # 영화 메타데이터와 병합하여 장르 정보 가져오기
            movie_metadata = self._get_movie_metadata_from_firestore()
            if movie_metadata.empty:
                return []

            # 사용자 평점과 영화 메타데이터 병합
            user_movies = pd.merge(user_ratings, movie_metadata[["movie_id", "genre"]], on="movie_id", how="left")

            # 장르별 평점 분석
            genre_ratings = user_movies.groupby("genre")["rating"].agg(["mean", "count"])
            genre_ratings = genre_ratings[genre_ratings["count"] >= 2]  # 2개 이상 평점이 있는 장르만

            # 평균 평점이 높은 장르 순으로 정렬
            preferred_genres = genre_ratings.sort_values("mean", ascending=False).index.tolist()

            return preferred_genres[:5]  # 상위 5개 장르

        except Exception as e:
            logger.error(f"선호 장르 분석 실패: {e}")
            return []

    def _get_rating_trend(self, user_ratings: pd.DataFrame) -> Dict[str, Any]:
        """평점 트렌드 분석"""
        try:
            if user_ratings.empty:
                return {}

            # 날짜별 평점 분석
            user_ratings["date"] = pd.to_datetime(user_ratings["created_at"]).dt.date
            daily_ratings = user_ratings.groupby("date")["rating"].mean()

            return {
                "recent_avg": daily_ratings.tail(7).mean() if len(daily_ratings) >= 7 else daily_ratings.mean(),
                "trend": "improving"
                if len(daily_ratings) >= 2 and daily_ratings.iloc[-1] > daily_ratings.iloc[-2]
                else "stable",
            }

        except Exception as e:
            logger.error(f"평점 트렌드 분석 실패: {e}")
            return {}


def show_firebase_recommendation_ui():
    """Firebase 기반 추천 UI"""
    # 사용자 인증 확인
    user = require_firebase_auth()
    if not user:
        return

    user_id = get_current_user_uid()
    if not user_id:
        st.error("사용자 ID를 찾을 수 없습니다.")
        return

    st.subheader("🎯 개인화 추천 시스템")

    # 추천 시스템 초기화
    try:
        recommender = FirebaseRecommender()

        if not recommender.svd_model and not recommender.item_based_model:
            st.warning("⚠️ 추천 모델이 로드되지 않았습니다. 인기 영화를 추천합니다.")

        # 추천 옵션
        col1, col2 = st.columns([2, 1])

        with col1:
            n_recommendations = st.slider("추천 개수", 5, 20, 10)

        with col2:
            st.write("")  # 공간

        # 추천 생성
        if st.button("🎬 추천 받기", type="primary"):
            with st.spinner("추천 영화를 찾는 중..."):
                try:
                    top_watched, recommendations = recommender.recommend_for_user(user_id, n_recommendations)

                    if recommendations.empty:
                        st.warning("추천할 영화가 없습니다.")
                    else:
                        st.success(f"**{len(recommendations)}개**의 영화를 추천합니다!")

                        # 사용자가 재밌게 본 영화 표시
                        if not top_watched.empty:
                            st.markdown("### 🌟 내가 재밌게 본 영화")

                            for _idx, row in top_watched.head(5).iterrows():
                                st.write(f"**{row.get('title', 'Unknown')}** - {row['rating']}/5.0")

                        st.markdown("---")
                        st.markdown("### 🎁 AI 추천 영화")

                        # 추천 영화 표시
                        for _idx, row in recommendations.iterrows():
                            with st.container():
                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    st.write(f"**{row.get('title', 'Unknown')}** ({row.get('year', 'N/A')})")
                                    if pd.notna(row.get("genre")):
                                        st.write(f"장르: {row['genre']}")
                                    if pd.notna(row.get("plot")):
                                        st.write(f"줄거리: {row['plot'][:100]}...")

                                with col2:
                                    if "predicted_rating" in row:
                                        st.metric("예측 평점", f"{row['predicted_rating']:.1f}/5.0")
                                    elif "similarity" in row:
                                        st.metric("유사도", f"{row['similarity']:.2f}")
                                    else:
                                        st.metric("인기도", f"{row.get('popularity', 'N/A')}")

                                st.markdown("---")

                except Exception as e:
                    st.error(f"추천 생성 중 오류가 발생했습니다: {e}")
                    logger.error(f"추천 생성 실패: {e}")

        # 사용자 통계
        st.markdown("### 📊 내 추천 통계")

        try:
            stats = recommender.get_user_recommendation_stats(user_id)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("총 평점 수", f"{stats.get('total_ratings', 0)}개")
                st.metric("평균 평점", f"{stats.get('avg_rating', 0):.1f}/5.0")

            with col2:
                preferred_genres = stats.get("preferred_genres", [])
                if preferred_genres:
                    st.write("**선호 장르:**")
                    for genre in preferred_genres[:3]:
                        st.write(f"• {genre}")
                else:
                    st.write("**선호 장르:** 분석 중...")

            with col3:
                rating_trend = stats.get("rating_trend", {})
                if rating_trend:
                    st.write(f"**최근 평균:** {rating_trend.get('recent_avg', 0):.1f}/5.0")
                    st.write(f"**트렌드:** {rating_trend.get('trend', 'stable')}")

        except Exception as e:
            st.error(f"통계 조회 중 오류가 발생했습니다: {e}")
            logger.error(f"통계 조회 실패: {e}")

    except Exception as e:
        st.error(f"추천 시스템 초기화 실패: {e}")
        logger.error(f"추천 시스템 초기화 실패: {e}")


def show_similar_movies_ui():
    """유사 영화 찾기 UI"""
    user = require_firebase_auth()
    if not user:
        return

    st.subheader("🔍 유사 영화 찾기")

    try:
        recommender = FirebaseRecommender()

        if not recommender.item_based_model:
            st.warning("⚠️ Item-Based 모델이 로드되지 않았습니다.")
            return

        # 영화 검색
        search_query = st.text_input("영화 제목을 검색하세요", placeholder="예: 타이타닉, 어벤져스, 기생충...")

        if search_query and search_query.strip():
            try:
                # 영화 검색
                firestore_manager = FirestoreManager()
                search_results = firestore_manager.search_movies(search_query, limit=10)

                if not search_results.empty:
                    st.write(f"**{len(search_results)}개**의 영화를 찾았습니다.")

                    # 영화 선택
                    selected_movie = st.selectbox("영화를 선택하세요", search_results["title"].tolist())

                    if selected_movie:
                        selected_movie_data = search_results[search_results["title"] == selected_movie].iloc[0]

                        # 선택한 영화 정보 표시
                        st.markdown("### 📽️ 선택한 영화")
                        st.write(f"**{selected_movie_data['title']}** ({selected_movie_data.get('year', 'N/A')})")
                        if pd.notna(selected_movie_data.get("genre")):
                            st.write(f"장르: {selected_movie_data['genre']}")

                        # 유사 영화 찾기
                        if st.button("🎬 유사 영화 찾기"):
                            with st.spinner("유사 영화를 찾는 중..."):
                                similar_movies = recommender.find_similar_movies(selected_movie_data["movie_id"], n=10)

                                if similar_movies.empty:
                                    st.warning("유사한 영화를 찾을 수 없습니다.")
                                else:
                                    st.success(f"**{len(similar_movies)}개**의 유사한 영화를 찾았습니다!")

                                    # 유사 영화 표시
                                    for _idx, row in similar_movies.iterrows():
                                        with st.container():
                                            col1, col2 = st.columns([3, 1])

                                            with col1:
                                                st.write(
                                                    f"**{row.get('title', 'Unknown')}** ({row.get('year', 'N/A')})"
                                                )
                                                if pd.notna(row.get("genre")):
                                                    st.write(f"장르: {row['genre']}")

                                            with col2:
                                                if "similarity" in row:
                                                    st.metric("유사도", f"{row['similarity']:.2f}")
                                                elif "similarity_score" in row:
                                                    st.metric("유사도", f"{row['similarity_score']:.2f}")

                                            st.markdown("---")
                else:
                    st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")

            except Exception as e:
                st.error(f"영화 검색 중 오류가 발생했습니다: {e}")
                logger.error(f"영화 검색 실패: {e}")

    except Exception as e:
        st.error(f"유사 영화 찾기 시스템 초기화 실패: {e}")
        logger.error(f"유사 영화 찾기 시스템 초기화 실패: {e}")


if __name__ == "__main__":
    st.title("Firebase 추천 시스템 테스트")

    tab1, tab2 = st.tabs(["🎯 개인화 추천", "🔍 유사 영화 찾기"])

    with tab1:
        show_firebase_recommendation_ui()

    with tab2:
        show_similar_movies_ui()
