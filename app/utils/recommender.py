"""
영화 추천 시스템 모듈
"""
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st
from typing import Tuple, Dict


class MovieRecommender:
    """영화 추천 시스템 클래스"""
    
    def __init__(self):
        self.user_movie_matrix = None
        self.predicted_ratings = None
        self.item_similarity = None
        self.content_similarity = None
        self.movie_to_idx = None
        self.idx_to_movie = None
        self.user_to_idx = None
        self.idx_to_user = None
        
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
    def train_item_based(_self, df_ratings: pd.DataFrame):
        """Item-based 협업 필터링 학습"""
        if _self.user_movie_matrix is None:
            raise ValueError("먼저 collaborative filtering을 학습해주세요")
        
        # Item-Item 유사도 계산
        item_user_matrix = _self.user_movie_matrix.T
        _self.item_similarity = cosine_similarity(item_user_matrix, dense_output=False)
        
        return True
    
    @st.cache_resource
    def train_content_based(_self, df_movies: pd.DataFrame):
        """컨텐츠 기반 필터링 학습"""
        # 장르와 줄거리를 결합
        df_movies['content'] = df_movies['genre'].fillna('') + ' ' + df_movies['plot'].fillna('')
        
        # TF-IDF 벡터화
        tfidf = TfidfVectorizer(max_features=3000, stop_words=None)
        tfidf_matrix = tfidf.fit_transform(df_movies['content'])
        
        # 코사인 유사도 계산
        _self.content_similarity = cosine_similarity(tfidf_matrix, tfidf_matrix)
        
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
            recommendations_df = recommendations_df.sort_values('predicted_rating', ascending=False)
            recommendations_df = recommendations_df.head(n_recommendations)
        
        return recommendations_df
    
    def find_similar_movies(self, movie_id: str, df_movies: pd.DataFrame, 
                           n_recommendations: int = 10, method: str = 'content') -> pd.DataFrame:
        """유사한 영화 찾기"""
        if movie_id not in df_movies['movie_id'].values:
            return pd.DataFrame()
        
        movie_idx = df_movies[df_movies['movie_id'] == movie_id].index[0]
        
        # 유사도 행렬 선택
        if method == 'content' and self.content_similarity is not None:
            similarity_scores = list(enumerate(self.content_similarity[movie_idx]))
        elif method == 'collaborative' and self.item_similarity is not None:
            idx = self.movie_to_idx.get(movie_id)
            if idx is not None:
                similarity_scores = list(enumerate(self.item_similarity[idx].toarray().flatten()))
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
        
        # 유사도 기준 정렬
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:n_recommendations+1]
        
        # 추천 영화 정보 생성
        recommendations = []
        for idx, score in similarity_scores:
            if method == 'content':
                movie_info = df_movies.iloc[idx]
            else:
                movie_id_similar = self.idx_to_movie.get(idx)
                if movie_id_similar:
                    movie_info = df_movies[df_movies['movie_id'] == movie_id_similar].iloc[0]
                else:
                    continue
            
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
        
        # 컨텐츠 기반 점수 계산
        cb_scores = np.zeros(len(df_movies))
        user_high_rated = df_ratings[(df_ratings['user_id'] == user_id) & 
                                     (df_ratings['rating'] >= 4.0)]
        
        for _, row in user_high_rated.iterrows():
            movie_id = row['movie_id']
            movie_indices = df_movies[df_movies['movie_id'] == movie_id].index
            
            if len(movie_indices) > 0 and self.content_similarity is not None:
                idx = movie_indices[0]
                sim_scores = self.content_similarity[idx]
                cb_scores += sim_scores
        
        # 정규화
        if cb_scores.max() > 0:
            cb_scores = cb_scores / cb_scores.max() * 5
        
        # 하이브리드 점수 계산
        recommendations = []
        for movie_idx, (movie_id, movie_data) in enumerate(df_movies.iterrows()):
            if movie_data['movie_id'] not in user_ratings:
                # CF 점수 가져오기
                cf_movie_idx = self.movie_to_idx.get(movie_data['movie_id'])
                if cf_movie_idx is not None and cf_movie_idx < len(cf_scores):
                    cf_score = cf_scores[cf_movie_idx]
                else:
                    cf_score = 0
                
                cb_score = cb_scores[movie_idx]
                hybrid_score = cf_weight * cf_score + cb_weight * cb_score
                
                recommendations.append({
                    'movie_id': movie_data['movie_id'],
                    'title': movie_data['title'],
                    'genre': movie_data['genre'],
                    'year': movie_data['year'],
                    'hybrid_score': hybrid_score,
                    'cf_score': cf_score,
                    'cb_score': cb_score,
                    'avg_score': movie_data['avg_score']
                })
        
        recommendations_df = pd.DataFrame(recommendations)
        if not recommendations_df.empty:
            recommendations_df = recommendations_df.sort_values('hybrid_score', ascending=False)
            recommendations_df = recommendations_df.head(n_recommendations)
        
        return recommendations_df

