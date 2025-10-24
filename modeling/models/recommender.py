"""
영화 추천 시스템 모듈 - 추천 전략별 모델을 불러와서 사용하는 래퍼 클래스
"""
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# SVD 파이프라인 import
from .svd import SVDRecommenderPipeline


class MovieRecommender:
    """
    영화 추천 시스템 래퍼 클래스
    
    추천 전략별로 저장된 모델을 불러와서 사용합니다:
    - CF (Collaborative Filtering): SVDRecommenderPipeline
    - Content-Based: TF-IDF 벡터화
    - Hybrid: CF + Content-Based 조합
    """
    
    def __init__(self, svd_pipeline_path: str = None):
        """
        Args:
            svd_pipeline_path: SVD 파이프라인 pkl 파일 경로
        """
        # CF 모델 (SVDRecommenderPipeline)
        self.svd_pipeline = None
        if svd_pipeline_path:
            self.load_svd_pipeline(svd_pipeline_path)
        
        # Content-based 필터링 (TF-IDF)
        self.tfidf = None
        self.tfidf_matrix = None
        self.df_movies_content = None  # TF-IDF 학습에 사용된 영화 데이터
    
    def load_svd_pipeline(self, filepath: str):
        """
        저장된 SVD 파이프라인 모델을 로드합니다.
        
        Args:
            filepath: SVD 파이프라인 pkl 파일 경로
        """
        self.svd_pipeline = SVDRecommenderPipeline.load_model(filepath)
        return True
    
    def train_content_based(self, df_movies: pd.DataFrame):
        """
        컨텐츠 기반 필터링 학습 (TF-IDF)
        
        Args:
            df_movies: 영화 정보 데이터프레임 (genre, plot 컬럼 필요)
        """
        # 장르와 줄거리를 결합
        df_movies = df_movies.copy()
        df_movies['content'] = df_movies['genre'].fillna('') + ' ' + df_movies['plot'].fillna('')
        
        # TF-IDF 벡터화
        self.tfidf = TfidfVectorizer(max_features=2000, stop_words=None)
        self.tfidf_matrix = self.tfidf.fit_transform(df_movies['content'])
        self.df_movies_content = df_movies
        
        return True
    
    def recommend_for_user(self, user_id: str, df_movies: pd.DataFrame, 
                          n_recommendations: int = 10):
        """
        특정 사용자에게 영화 추천 (협업 필터링 - CF 기반)
        
        Args:
            user_id: 사용자 ID
            df_movies: 영화 정보 데이터프레임
            n_recommendations: 추천할 영화 개수
            
        Returns:
            (top_watched, recommendations) 튜플
            - top_watched: 사용자가 높게 평가한 영화 DataFrame
            - recommendations: 추천 영화 DataFrame
        """
        if self.svd_pipeline is None:
            raise ValueError("SVD 파이프라인을 먼저 로드해주세요. load_svd_pipeline() 실행 필요")
        
        # SVD 파이프라인으로 추천
        top_watched, recommendations = self.svd_pipeline.recommend_for_user(
            user_id, df_movies, n=n_recommendations
        )
        
        return top_watched, recommendations
    
    def get_user_top_watched(self, user_id: str, df_movies: pd.DataFrame, 
                            n: int = 10) -> pd.DataFrame:
        """
        사용자가 높게 평가한 영화 조회
        
        Args:
            user_id: 사용자 ID
            df_movies: 영화 정보 데이터프레임
            n: 조회할 영화 개수
            
        Returns:
            높게 평가한 영화 데이터프레임
        """
        if self.svd_pipeline is None:
            raise ValueError("SVD 파이프라인을 먼저 로드해주세요.")
        
        top_watched, _ = self.svd_pipeline.recommend_for_user(
            user_id, df_movies, n=n
        )
        
        return top_watched
    
    def find_similar_movies(self, movie_id: str, df_movies: pd.DataFrame, 
                           n_recommendations: int = 10, method: str = 'content') -> pd.DataFrame:
        """
        유사한 영화 찾기
        
        Args:
            movie_id: 기준 영화 ID
            df_movies: 영화 정보 데이터프레임
            n_recommendations: 추천할 영화 개수
            method: 'content' 또는 'collaborative'
            
        Returns:
            유사한 영화 데이터프레임
        """
        if movie_id not in df_movies['movie_id'].values:
            return pd.DataFrame()
        
        if method == 'content':
            return self._find_similar_by_content(movie_id, df_movies, n_recommendations)
        elif method == 'collaborative':
            return self._find_similar_by_collaborative(movie_id, df_movies, n_recommendations)
        else:
            raise ValueError(f"지원하지 않는 method: {method}")
    
    def _find_similar_by_content(self, movie_id: str, df_movies: pd.DataFrame, 
                                 n: int) -> pd.DataFrame:
        """컨텐츠 기반 유사 영화 찾기"""
        if self.tfidf_matrix is None:
            raise ValueError("Content-based 모델을 먼저 학습해주세요. train_content_based() 실행 필요")
        
        # df_movies_content에서 movie_id의 인덱스 찾기
        movie_idx = self.df_movies_content[self.df_movies_content['movie_id'] == movie_id].index[0]
        
        # 선택한 영화의 TF-IDF 벡터
        movie_vector = self.tfidf_matrix[movie_idx]
        
        # 모든 영화와의 유사도 계산
        similarities = cosine_similarity(movie_vector, self.tfidf_matrix).flatten()
        similarity_scores = list(enumerate(similarities))
        
        # 유사도 기준 정렬 (자기 자신 제외)
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:n+1]
        
        # 추천 영화 ID와 유사도
        recommendations = []
        for idx, score in similarity_scores:
            movie_info = self.df_movies_content.iloc[idx]
            recommendations.append({
                'movie_id': movie_info['movie_id'],
                'similarity': score
            })
        
        # 전체 영화 정보와 merge
        recommendations_df = pd.DataFrame(recommendations)
        recommendations_df = pd.merge(recommendations_df, df_movies, on='movie_id', how='left')
        
        return recommendations_df
    
    def _find_similar_by_collaborative(self, movie_id: str, df_movies: pd.DataFrame, 
                                       n: int) -> pd.DataFrame:
        """협업 필터링 기반 유사 영화 찾기"""
        if self.svd_pipeline is None:
            raise ValueError("SVD 파이프라인을 먼저 로드해주세요.")
        
        # SVD 파이프라인의 df_preprocessed에서 사용자 목록 가져오기
        user_ids = self.svd_pipeline.df_preprocessed['user_id'].unique()
        
        # 기준 영화의 평점 벡터 생성
        base_movie_ratings = []
        for user_id in user_ids:
            pred = self.svd_pipeline.predict(user_id, movie_id)
            base_movie_ratings.append(pred)
        base_movie_ratings = np.array(base_movie_ratings).reshape(1, -1)
        
        # 다른 영화들의 평점 벡터 생성 및 유사도 계산
        similarity_scores = []
        for other_movie_id in df_movies['movie_id']:
            if other_movie_id != movie_id:
                other_movie_ratings = []
                for user_id in user_ids:
                    pred = self.svd_pipeline.predict(user_id, other_movie_id)
                    other_movie_ratings.append(pred)
                other_movie_ratings = np.array(other_movie_ratings).reshape(1, -1)
                
                # 코사인 유사도 계산
                sim = cosine_similarity(base_movie_ratings, other_movie_ratings)[0][0]
                similarity_scores.append((other_movie_id, sim))
        
        # 유사도 기준 정렬
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[:n]
        
        # 추천 영화 ID와 유사도
        recommendations = []
        for movie_id_rec, score in similarity_scores:
            recommendations.append({
                'movie_id': movie_id_rec,
                'similarity': score
            })
        
        # 전체 영화 정보와 merge
        recommendations_df = pd.DataFrame(recommendations)
        recommendations_df = pd.merge(recommendations_df, df_movies, on='movie_id', how='left')
        
        return recommendations_df
