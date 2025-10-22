"""
영화 추천 시스템 모듈 (경량화 버전 - 배포용)
유사도 행렬을 미리 계산하지 않고 on-demand로 계산
"""
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st
from typing import Tuple, Dict


class MovieRecommenderLite:
    """영화 추천 시스템 클래스 (경량화 버전)"""
    
    def __init__(self):
        self.user_movie_matrix = None
        self.predicted_ratings = None
        self.movie_to_idx = None
        self.idx_to_movie = None
        self.user_to_idx = None
        self.idx_to_user = None
        # 컨텐츠 기반 - TF-IDF 벡터만 저장
        self.tfidf = None
        self.tfidf_matrix = None
        
    @st.cache_resource
    def train_collaborative_filtering(_self, df_ratings: pd.DataFrame, n_factors: int = 50):
        """협업 필터링 모델 학습 (SVD)"""
        # ID 매핑
        unique_users = sorted(df_ratings['user_id'].unique())
        unique_movies = sorted(df_ratings['movie_id'].unique())
        
        _self.user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        _self.idx_to_user = {idx: user_id for user_id, idx in _self.user_to_idx.items()}
        _self.movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
        _self.idx_to_movie = {idx: movie_id for movie_id, idx in _self.movie_to_idx.items()}
        
        # User-Movie 행렬 생성
        n_users = len(unique_users)
        n_movies = len(unique_movies)
        
        df_ratings['user_idx'] = df_ratings['user_id'].map(_self.user_to_idx)
        df_ratings['movie_idx'] = df_ratings['movie_id'].map(_self.movie_to_idx)
        
        _self.user_movie_matrix = csr_matrix(
            (df_ratings['rating'], (df_ratings['user_idx'], df_ratings['movie_idx'])),
            shape=(n_users, n_movies)
        )
        
        # SVD 수행
        matrix_dense = _self.user_movie_matrix.toarray()
        user_ratings_mean = np.mean(matrix_dense, axis=1)
        matrix_centered = matrix_dense - user_ratings_mean.reshape(-1, 1)
        
        U, sigma, Vt = svds(matrix_centered, k=n_factors)
        sigma = np.diag(sigma)
        
        _self.predicted_ratings = np.dot(np.dot(U, sigma), Vt) + user_ratings_mean.reshape(-1, 1)
        
        return True
    
    @st.cache_resource
    def train_content_based(_self, df_movies: pd.DataFrame):
        """컨텐츠 기반 필터링 학습 (TF-IDF만 저장, 유사도는 on-demand)"""
        # 장르와 줄거리를 결합
        df_movies['content'] = df_movies['genre'].fillna('') + ' ' + df_movies['plot'].fillna('')
        
        # TF-IDF 벡터화
        _self.tfidf = TfidfVectorizer(max_features=3000, stop_words=None)
        _self.tfidf_matrix = _self.tfidf.fit_transform(df_movies['content'])
        
        return True
    
    def recommend_for_user(self, user_id: str, df_movies: pd.DataFrame, 
                          df_ratings: pd.DataFrame, n_recommendations: int = 10) -> pd.DataFrame:
        """특정 사용자에게 영화 추천 (협업 필터링)"""
        if user_id not in self.user_to_idx:
            return pd.DataFrame()
        
        user_idx = self.user_to_idx[user_id]
        user_ratings = df_ratings[df_ratings['user_id'] == user_id]['movie_id'].values
        
        # 예측 평점 가져오기
        user_predictions = self.predicted_ratings[user_idx]
        
        # 추천 영화 목록 생성
        recommendations = []
        for movie_idx, predicted_rating in enumerate(user_predictions):
            movie_id = self.idx_to_movie.get(movie_idx)
            if movie_id and movie_id not in user_ratings:
                movie_info = df_movies[df_movies['movie_id'] == movie_id]
                if not movie_info.empty:
                    recommendations.append({
                        'movie_id': movie_id,
                        'title': movie_info.iloc[0]['title'],
                        'genre': movie_info.iloc[0]['genre'],
                        'year': movie_info.iloc[0]['year'],
                        'predicted_rating': predicted_rating,
                        'avg_score': movie_info.iloc[0]['avg_score']
                    })
        
        # 상위 N개 추천
        recommendations_df = pd.DataFrame(recommendations)
        if not recommendations_df.empty:
            recommendations_df = recommendations_df.sort_values('predicted_rating', ascending=False).head(n_recommendations)
        
        return recommendations_df
    
    def find_similar_movies(self, movie_id: str, df_movies: pd.DataFrame, 
                           n_recommendations: int = 10, method: str = 'content') -> pd.DataFrame:
        """유사한 영화 찾기 (on-demand 계산)"""
        if movie_id not in df_movies['movie_id'].values:
            return pd.DataFrame()
        
        movie_idx = df_movies[df_movies['movie_id'] == movie_id].index[0]
        
        if method == 'content' and self.tfidf_matrix is not None:
            # 선택한 영화의 TF-IDF 벡터
            movie_vector = self.tfidf_matrix[movie_idx]
            # 모든 영화와의 유사도 계산 (on-demand)
            similarities = cosine_similarity(movie_vector, self.tfidf_matrix).flatten()
            similarity_scores = list(enumerate(similarities))
        elif method == 'collaborative' and self.user_movie_matrix is not None:
            idx = self.movie_to_idx.get(movie_id)
            if idx is None:
                return pd.DataFrame()
            # 해당 영화의 벡터
            item_vector = self.user_movie_matrix.T[idx]
            # 모든 영화와의 유사도 계산 (on-demand)
            similarities = cosine_similarity(item_vector, self.user_movie_matrix.T).flatten()
            
            # movie_idx를 실제 df_movies 인덱스로 변환
            similarity_scores = []
            for movie_idx_cf, score in enumerate(similarities):
                movie_id_cf = self.idx_to_movie.get(movie_idx_cf)
                if movie_id_cf:
                    df_idx = df_movies[df_movies['movie_id'] == movie_id_cf].index
                    if len(df_idx) > 0:
                        similarity_scores.append((df_idx[0], score))
        else:
            return pd.DataFrame()
        
        # 유사도 기준 정렬
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:n_recommendations+1]
        
        # 추천 영화 정보 생성
        recommendations = []
        for idx, score in similarity_scores:
            movie_info = df_movies.iloc[idx]
            recommendations.append({
                'title': movie_info['title'],
                'genre': movie_info['genre'],
                'year': movie_info['year'],
                'avg_score': movie_info['avg_score'],
                'similarity': score
            })
        
        return pd.DataFrame(recommendations)
    
    def hybrid_recommend(self, user_id: str, df_movies: pd.DataFrame, 
                        df_ratings: pd.DataFrame, n_recommendations: int = 10,
                        cf_weight: float = 0.6, cb_weight: float = 0.4) -> pd.DataFrame:
        """하이브리드 추천 (협업 + 컨텐츠)"""
        if user_id not in self.user_to_idx:
            return pd.DataFrame()
        
        user_idx = self.user_to_idx[user_id]
        user_ratings = df_ratings[df_ratings['user_id'] == user_id]['movie_id'].values
        
        # 협업 필터링 점수
        cf_scores = self.predicted_ratings[user_idx]
        
        # 사용자가 본 영화들의 평균 컨텐츠 벡터 계산
        user_movie_indices = df_movies[df_movies['movie_id'].isin(user_ratings)].index.tolist()
        if len(user_movie_indices) > 0 and self.tfidf_matrix is not None:
            user_profile = self.tfidf_matrix[user_movie_indices].mean(axis=0)
            # 모든 영화와의 컨텐츠 유사도
            cb_scores_raw = cosine_similarity(user_profile, self.tfidf_matrix).flatten()
        else:
            cb_scores_raw = np.zeros(len(df_movies))
        
        # 하이브리드 점수 계산
        recommendations = []
        for movie_idx, cf_score in enumerate(cf_scores):
            movie_id = self.idx_to_movie.get(movie_idx)
            if movie_id and movie_id not in user_ratings:
                movie_info = df_movies[df_movies['movie_id'] == movie_id]
                if not movie_info.empty:
                    df_idx = movie_info.index[0]
                    cb_score = cb_scores_raw[df_idx]
                    
                    # 정규화
                    cf_normalized = (cf_score - cf_scores.min()) / (cf_scores.max() - cf_scores.min() + 1e-10)
                    cb_normalized = cb_score  # 이미 0-1 사이
                    
                    hybrid_score = cf_weight * cf_normalized + cb_weight * cb_normalized
                    
                    recommendations.append({
                        'movie_id': movie_id,
                        'title': movie_info.iloc[0]['title'],
                        'genre': movie_info.iloc[0]['genre'],
                        'year': movie_info.iloc[0]['year'],
                        'avg_score': movie_info.iloc[0]['avg_score'],
                        'hybrid_score': hybrid_score,
                        'cf_score': cf_score,
                        'cb_score': cb_score
                    })
        
        # 상위 N개 추천
        recommendations_df = pd.DataFrame(recommendations)
        if not recommendations_df.empty:
            recommendations_df = recommendations_df.sort_values('hybrid_score', ascending=False).head(n_recommendations)
        
        return recommendations_df

