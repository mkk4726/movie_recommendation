"""
영화 추천 시스템 모듈 (Surprise SVD 기반 - 배포용, Streamlit 데코레이터 없는 깔끔한 버전)
"""
import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer


class MovieRecommenderLite:
    """영화 추천 시스템 클래스 (Surprise SVD 기반 - 경량화)"""
    
    def __init__(self):
        self.svd_model = None
        # trainset은 학습 후 삭제 (불필요)
        self.movie_to_idx = None
        self.idx_to_movie = None
        self.user_to_idx = None
        self.idx_to_user = None
        # 컨텐츠 기반 - TF-IDF 벡터만 저장
        self.tfidf = None
        self.tfidf_matrix = None
        # df_ratings_train 제거 (불필요한 중복 데이터)
        
    def train_collaborative_filtering(self, df_ratings: pd.DataFrame, n_factors: int = 20):
        """협업 필터링 모델 학습 (Surprise SVD - 경량화)"""
        # ID 매핑
        unique_users = sorted(df_ratings['user_id'].unique())
        unique_movies = sorted(df_ratings['movie_id'].unique())
        
        self.user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        self.idx_to_user = {idx: user_id for user_id, idx in self.user_to_idx.items()}
        self.movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
        self.idx_to_movie = {idx: movie_id for movie_id, idx in self.movie_to_idx.items()}
        
        # Surprise Dataset 생성
        reader = Reader(rating_scale=(df_ratings['rating'].min(), df_ratings['rating'].max()))
        
        # DataFrame을 Surprise Dataset으로 변환
        data = Dataset.load_from_df(
            df_ratings[['user_id', 'movie_id', 'rating']], 
            reader
        )
        
        # 전체 데이터로 학습
        trainset = data.build_full_trainset()
        
        # SVD 모델 생성 및 학습 (경량화 파라미터)
        self.svd_model = SVD(
            n_factors=n_factors,  # 50 -> 20으로 축소 (메모리 절약)
            n_epochs=15,  # 20 -> 15로 축소
            lr_all=0.005,
            reg_all=0.02,
            random_state=42,
            verbose=False
        )
        
        self.svd_model.fit(trainset)
        
        # trainset은 학습 후 필요 없으므로 저장하지 않음 (메모리 절약)
        
        return True
    
    def train_content_based(self, df_movies: pd.DataFrame):
        """컨텐츠 기반 필터링 학습 (TF-IDF만 저장, 유사도는 on-demand)"""
        # 장르와 줄거리를 결합
        df_movies['content'] = df_movies['genre'].fillna('') + ' ' + df_movies['plot'].fillna('')
        
        # TF-IDF 벡터화 (경량화: 2000개 특징으로 축소)
        self.tfidf = TfidfVectorizer(max_features=2000, stop_words=None)
        self.tfidf_matrix = self.tfidf.fit_transform(df_movies['content'])
        
        return True
    
    def recommend_for_user(self, user_id: str, df_movies: pd.DataFrame, 
                          df_ratings: pd.DataFrame, n_recommendations: int = 10) -> pd.DataFrame:
        """특정 사용자에게 영화 추천 (협업 필터링)"""
        if user_id not in self.user_to_idx:
            return pd.DataFrame()
        
        # 사용자가 이미 본 영화들
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
        elif method == 'collaborative' and self.svd_model is not None:
            # 협업 필터링 기반 유사도: 사용자 평점 패턴으로 계산
            # 각 영화에 대해 모든 사용자의 예상 평점 벡터 생성
            if movie_id not in self.movie_to_idx:
                return pd.DataFrame()
            
            # 기준 영화의 평점 벡터 생성
            base_movie_ratings = []
            for user_id in self.user_to_idx.keys():
                pred = self.svd_model.predict(user_id, movie_id).est
                base_movie_ratings.append(pred)
            base_movie_ratings = np.array(base_movie_ratings).reshape(1, -1)
            
            # 다른 영화들의 평점 벡터 생성 및 유사도 계산
            similarity_scores = []
            for idx, other_movie_id in enumerate(df_movies['movie_id']):
                if other_movie_id in self.movie_to_idx:
                    other_movie_ratings = []
                    for user_id in self.user_to_idx.keys():
                        pred = self.svd_model.predict(user_id, other_movie_id).est
                        other_movie_ratings.append(pred)
                    other_movie_ratings = np.array(other_movie_ratings).reshape(1, -1)
                    
                    # 코사인 유사도 계산
                    sim = cosine_similarity(base_movie_ratings, other_movie_ratings)[0][0]
                    similarity_scores.append((idx, sim))
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
        
        user_ratings = df_ratings[df_ratings['user_id'] == user_id]['movie_id'].values
        
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
        cf_scores_list = []
        
        # 먼저 모든 CF 점수 수집 (정규화를 위해)
        for movie_id in self.movie_to_idx.keys():
            if movie_id not in user_ratings:
                cf_score = self.svd_model.predict(user_id, movie_id).est
                cf_scores_list.append(cf_score)
        
        # CF 점수 정규화를 위한 min/max
        if cf_scores_list:
            cf_min = min(cf_scores_list)
            cf_max = max(cf_scores_list)
        else:
            cf_min, cf_max = 0, 5
        
        for movie_id in self.movie_to_idx.keys():
            if movie_id not in user_ratings:
                movie_info = df_movies[df_movies['movie_id'] == movie_id]
                if not movie_info.empty:
                    # CF 점수
                    cf_score = self.svd_model.predict(user_id, movie_id).est
                    
                    # CB 점수
                    df_idx = movie_info.index[0]
                    cb_score = cb_scores_raw[df_idx]
                    
                    # 정규화
                    cf_normalized = (cf_score - cf_min) / (cf_max - cf_min + 1e-10)
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
