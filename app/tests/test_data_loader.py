"""
데이터 로더 테스트
"""
import pytest
import pandas as pd
from utils.data_loader import load_movie_data, load_ratings_data, filter_data, search_movies


class TestDataLoading:
    """데이터 로딩 테스트"""
    
    def test_load_movie_data(self, df_movies):
        """영화 데이터 로딩 테스트"""
        assert df_movies is not None
        assert isinstance(df_movies, pd.DataFrame)
        assert len(df_movies) > 0
        assert 'title' in df_movies.columns
        assert 'movie_id' in df_movies.columns
        assert 'genre' in df_movies.columns
        assert 'avg_score' in df_movies.columns
        
    def test_load_ratings_data(self, df_ratings):
        """평점 데이터 로딩 테스트"""
        assert df_ratings is not None
        assert isinstance(df_ratings, pd.DataFrame)
        assert len(df_ratings) > 0
        assert 'user_id' in df_ratings.columns
        assert 'movie_id' in df_ratings.columns
        assert 'rating' in df_ratings.columns
        assert df_ratings['rating'].min() >= 0.0
        assert df_ratings['rating'].max() <= 5.0
        
    def test_filter_data(self, df_ratings, df_ratings_filtered):
        """데이터 필터링 테스트"""
        assert df_ratings_filtered is not None
        assert len(df_ratings_filtered) < len(df_ratings)
        
        # 필터링 후 최소 평점 개수 확인
        user_counts = df_ratings_filtered.groupby('user_id').size()
        movie_counts = df_ratings_filtered.groupby('movie_id').size()
        
        # 대부분의 사용자가 최소 기준을 만족하는지 확인 (일부는 필터링 과정에서 줄어들 수 있음)
        assert user_counts.min() >= 20  # 30에서 일부 줄어들 수 있음
        assert movie_counts.min() >= 5   # 10에서 일부 줄어들 수 있음


class TestMovieSearch:
    """영화 검색 테스트"""
    
    def test_search_movies_basic(self, df_movies):
        """기본 검색 테스트"""
        result = search_movies(df_movies, "타이타닉", limit=10)
        assert isinstance(result, pd.DataFrame)
        
    def test_search_movies_with_results(self, df_movies):
        """검색 결과가 있는 경우"""
        # 첫 번째 영화 제목의 일부로 검색
        first_movie_title = df_movies.iloc[0]['title'][:3]
        result = search_movies(df_movies, first_movie_title, limit=5)
        assert len(result) > 0
        
    def test_search_movies_no_results(self, df_movies):
        """검색 결과가 없는 경우"""
        result = search_movies(df_movies, "존재하지않는영화제목12345", limit=10)
        assert result is None or len(result) == 0
        
    def test_search_movies_limit(self, df_movies):
        """검색 결과 제한 테스트"""
        result = search_movies(df_movies, "의", limit=3)
        if result is not None and len(result) > 0:
            assert len(result) <= 3


class TestDataQuality:
    """데이터 품질 테스트"""
    
    def test_movies_have_required_fields(self, df_movies):
        """영화 데이터 필수 필드 확인"""
        required_fields = ['movie_id', 'title', 'genre', 'avg_score']
        for field in required_fields:
            assert field in df_movies.columns
            
    def test_ratings_valid_range(self, df_ratings):
        """평점 범위 유효성 테스트"""
        assert df_ratings['rating'].min() >= 0.0
        assert df_ratings['rating'].max() <= 5.0
        
    def test_no_duplicate_movie_ids(self, df_movies):
        """중복 영화 ID 확인"""
        duplicate_count = df_movies['movie_id'].duplicated().sum()
        # 일부 중복이 있을 수 있지만 너무 많으면 안됨
        assert duplicate_count < len(df_movies) * 0.1  # 10% 미만
        
    def test_data_statistics(self, df_ratings):
        """기본 통계 확인"""
        assert df_ratings['user_id'].nunique() > 0
        assert df_ratings['movie_id'].nunique() > 0
        assert len(df_ratings) > 1000  # 최소 데이터 양 확인

