"""
추천 시스템 테스트
"""
import pytest
import pandas as pd
from utils.recommender import MovieRecommender


@pytest.fixture(scope="module")
def recommender(df_ratings_filtered):
    """추천 시스템 fixture (모듈 전체에서 한 번만 학습)"""
    rec = MovieRecommender()
    rec.train_collaborative_filtering(df_ratings_filtered, n_factors=30)
    return rec


@pytest.fixture(scope="module")
def recommender_full(df_ratings_filtered, df_movies):
    """모든 모델이 학습된 추천 시스템 fixture"""
    rec = MovieRecommender()
    rec.train_collaborative_filtering(df_ratings_filtered, n_factors=30)
    rec.train_item_based(df_ratings_filtered)  # SVD 모델 기반으로 item similarity 계산
    rec.train_content_based(df_movies)
    return rec


class TestCollaborativeFiltering:
    """협업 필터링 테스트"""
    
    def test_train_collaborative_filtering(self, df_ratings_filtered):
        """협업 필터링 학습 테스트"""
        recommender = MovieRecommender()
        result = recommender.train_collaborative_filtering(df_ratings_filtered, n_factors=20)
        assert result is True
        assert recommender.svd_model is not None
        assert recommender.trainset is not None
        assert recommender.user_to_idx is not None
        assert recommender.movie_to_idx is not None
        
    def test_recommend_for_user(self, recommender, df_movies, df_ratings_filtered):
        """사용자 기반 추천 테스트"""
        test_user = df_ratings_filtered['user_id'].iloc[0]
        recommendations = recommender.recommend_for_user(
            test_user, df_movies, df_ratings_filtered, n_recommendations=5
        )
        
        assert isinstance(recommendations, pd.DataFrame)
        if not recommendations.empty:
            assert len(recommendations) <= 5
            assert 'title' in recommendations.columns
            assert 'predicted_rating' in recommendations.columns
            
    def test_recommend_for_invalid_user(self, recommender, df_movies, df_ratings_filtered):
        """존재하지 않는 사용자 추천 테스트"""
        recommendations = recommender.recommend_for_user(
            "invalid_user_id_12345", df_movies, df_ratings_filtered, n_recommendations=5
        )
        assert recommendations.empty


class TestItemBasedFiltering:
    """Item-based 필터링 테스트"""
    
    def test_train_item_based(self, recommender, df_ratings_filtered):
        """Item-based 학습 테스트"""
        result = recommender.train_item_based(df_ratings_filtered)  # SVD 모델 기반 item similarity
        assert result is True
        assert recommender.item_similarity is not None


class TestContentBasedFiltering:
    """컨텐츠 기반 필터링 테스트"""
    
    def test_train_content_based(self, df_movies):
        """컨텐츠 기반 학습 테스트"""
        recommender = MovieRecommender()
        result = recommender.train_content_based(df_movies)
        assert result is True
        assert recommender.content_similarity is not None
        
    def test_find_similar_movies_content(self, recommender_full, df_movies):
        """컨텐츠 기반 유사 영화 찾기 테스트"""
        test_movie_id = df_movies.iloc[100]['movie_id']
        similar_movies = recommender_full.find_similar_movies(
            test_movie_id, df_movies, n_recommendations=5, method='content'
        )
        
        assert isinstance(similar_movies, pd.DataFrame)
        if not similar_movies.empty:
            assert len(similar_movies) <= 5
            assert 'title' in similar_movies.columns
            assert 'similarity' in similar_movies.columns
            
    def test_find_similar_movies_collaborative(self, recommender_full, df_movies):
        """협업 필터링 기반 유사 영화 찾기 테스트"""
        test_movie_id = df_movies.iloc[100]['movie_id']
        similar_movies = recommender_full.find_similar_movies(
            test_movie_id, df_movies, n_recommendations=5, method='collaborative'
        )
        
        assert isinstance(similar_movies, pd.DataFrame)
        
    def test_find_similar_movies_invalid(self, recommender_full, df_movies):
        """존재하지 않는 영화 유사도 검색 테스트"""
        similar_movies = recommender_full.find_similar_movies(
            "invalid_movie_id_12345", df_movies, n_recommendations=5, method='content'
        )
        assert similar_movies.empty


class TestHybridRecommendation:
    """하이브리드 추천 테스트"""
    
    def test_hybrid_recommend(self, recommender_full, df_movies, df_ratings_filtered):
        """하이브리드 추천 테스트"""
        test_user = df_ratings_filtered['user_id'].iloc[0]
        recommendations = recommender_full.hybrid_recommend(
            test_user, df_movies, df_ratings_filtered, 
            n_recommendations=5, cf_weight=0.6, cb_weight=0.4
        )
        
        assert isinstance(recommendations, pd.DataFrame)
        if not recommendations.empty:
            assert len(recommendations) <= 5
            assert 'hybrid_score' in recommendations.columns
            assert 'cf_score' in recommendations.columns
            assert 'cb_score' in recommendations.columns
            
    def test_hybrid_recommend_weight_variation(self, recommender_full, df_movies, df_ratings_filtered):
        """하이브리드 추천 가중치 변화 테스트"""
        test_user = df_ratings_filtered['user_id'].iloc[0]
        
        # 협업 필터링 100%
        rec1 = recommender_full.hybrid_recommend(
            test_user, df_movies, df_ratings_filtered, 
            n_recommendations=3, cf_weight=1.0, cb_weight=0.0
        )
        
        # 컨텐츠 기반 100%
        rec2 = recommender_full.hybrid_recommend(
            test_user, df_movies, df_ratings_filtered, 
            n_recommendations=3, cf_weight=0.0, cb_weight=1.0
        )
        
        assert isinstance(rec1, pd.DataFrame)
        assert isinstance(rec2, pd.DataFrame)

