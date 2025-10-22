"""
영화 추천 시스템 모듈 (Surprise SVD 기반)
"""
import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st


class MovieRecommender:
    """영화 추천 시스템 클래스 (Surprise SVD 기반)"""
    
    def __init__(self):
        self.svd_model = None
        self.trainset = None
        self.item_similarity = None
        self.content_similarity = None
        self.movie_to_idx = None
        self.idx_to_movie = None
        self.user_to_idx = None
        self.idx_to_user = None
        self.tfidf = None
        self.tfidf_matrix = None
        self.df_ratings_train = None
        
    @st.cache_resource
    def train_collaborative_filtering(_self, df_ratings: pd.DataFrame, n_factors: int = 50):
        """협업 필터링 모델 학습 (Surprise SVD)"""
        # ID 매핑
        unique_users = sorted(df_ratings['user_id'].unique())
        unique_movies = sorted(df_ratings['movie_id'].unique())
        
        _self.user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        _self.idx_to_user = {idx: user_id for user_id, idx in _self.user_to_idx.items()}
        _self.movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
        _self.idx_to_movie = {idx: movie_id for movie_id, idx in _self.movie_to_idx.items()}
        
        # 학습 데이터 저장
        _self.df_ratings_train = df_ratings.copy()
        
        # Surprise Dataset 생성
        reader = Reader(rating_scale=(df_ratings['rating'].min(), df_ratings['rating'].max()))
        data = Dataset.load_from_df(
            df_ratings[['user_id', 'movie_id', 'rating']], 
            reader
        )
        
        # 전체 데이터로 학습
        _self.trainset = data.build_full_trainset()
        
        # SVD 모델 생성 및 학습
        _self.svd_model = SVD(
            n_factors=n_factors,
            n_epochs=20,
            lr_all=0.005,
            reg_all=0.02,
            random_state=42,
            verbose=False
        )
        
        _self.svd_model.fit(_self.trainset)
        
        return True
    
    @st.cache_resource
    def train_item_based(_self, df_ratings: pd.DataFrame):
        """Item-based 협업 필터링 학습 (Surprise SVD 기반)"""
        if _self.svd_model is None:
            raise ValueError("먼저 collaborative filtering을 학습해주세요")
        
        # 영화별 평점 벡터 생성 (사용자들의 예측 평점)
        movie_vectors = []
        movie_ids_list = list(_self.movie_to_idx.keys())
        
        for movie_id in movie_ids_list:
            movie_ratings = []
            for user_id in _self.user_to_idx.keys():
                pred = _self.svd_model.predict(user_id, movie_id).est
                movie_ratings.append(pred)
            movie_vectors.append(movie_ratings)
        
        # Item-Item 유사도 계산
        movie_vectors = np.array(movie_vectors)
        _self.item_similarity = cosine_similarity(movie_vectors, movie_vectors)
        
        return True
    
    @st.cache_resource
    def train_content_based(_self, df_movies: pd.DataFrame):
        """컨텐츠 기반 필터링 학습"""
        # 장르와 줄거리를 결합
        df_movies['content'] = df_movies['genre'].fillna('') + ' ' + df_movies['plot'].fillna('')
        
        # TF-IDF 벡터화
        _self.tfidf = TfidfVectorizer(max_features=3000, stop_words=None)
        _self.tfidf_matrix = _self.tfidf.fit_transform(df_movies['content'])
        
        # 코사인 유사도 계산
        _self.content_similarity = cosine_similarity(_self.tfidf_matrix, _self.tfidf_matrix)
        
        return True
    
    def recommend_for_user(self, user_id: str, df_movies: pd.DataFrame, 
                          df_ratings: pd.DataFrame, n_recommendations: int = 10) -> pd.DataFrame:
        """특정 사용자에게 영화 추천 (협업 필터링)"""
        if user_id not in self.user_to_idx:
            return pd.DataFrame()
        
        user_ratings = df_ratings[df_ratings['user_id'] == user_id]['movie_id'].values
        
        # 추천 영화 목록 생성
        recommendations = []
        for movie_id in self.movie_to_idx.keys():
            if movie_id not in user_ratings:
                # Surprise 모델로 예측
                predicted_rating = self.svd_model.predict(user_id, movie_id).est
                
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
                similarity_scores = list(enumerate(self.item_similarity[idx]))
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
        
        user_ratings = df_ratings[df_ratings['user_id'] == user_id]['movie_id'].values
        
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
                # CF 점수 가져오기 (Surprise 예측)
                if movie_data['movie_id'] in self.movie_to_idx:
                    cf_score = self.svd_model.predict(user_id, movie_data['movie_id']).est
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
