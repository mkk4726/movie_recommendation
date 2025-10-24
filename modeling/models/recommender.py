"""
영화 추천 시스템 모듈 - 추천 전략별 모델을 불러와서 사용하는 래퍼 클래스
"""
import pandas as pd

# SVD 파이프라인 import
try:
    from .svd import SVDRecommenderPipeline
    from .item_based import ItemBasedRecommender
except ImportError:
    from modeling.models.svd import SVDRecommenderPipeline
    from modeling.models.item_based import ItemBasedRecommender


class MovieRecommender:
    """
    영화 추천 시스템 래퍼 클래스
    
    추천 전략별로 저장된 모델을 불러와서 사용합니다:
    - CF (Collaborative Filtering): SVDRecommenderPipeline (사용자 맞춤 추천)
    - Item-Based CF: ItemBasedRecommender (영화 간 유사도 기반 추천)
    """
    
    def __init__(self, svd_pipeline_path: str = None, item_based_path: str = None):
        """
        Args:
            svd_pipeline_path: SVD 파이프라인 pkl 파일 경로
            item_based_path: Item-Based 모델 pkl 파일 경로
        """
        # CF 모델 (SVDRecommenderPipeline) - 사용자 맞춤 추천용
        self.svd_pipeline = None
        if svd_pipeline_path:
            self.load_svd_pipeline(svd_pipeline_path)
        
        # Item-Based CF 모델 - 영화 유사도 추천용
        self.item_based = None
        if item_based_path:
            self.load_item_based(item_based_path)
    
    def load_svd_pipeline(self, filepath: str):
        """
        저장된 SVD 파이프라인 모델을 로드합니다.
        
        Args:
            filepath: SVD 파이프라인 pkl 파일 경로
        """
        self.svd_pipeline = SVDRecommenderPipeline.load_model(filepath)
        return True
    
    def load_item_based(self, filepath: str):
        """
        저장된 Item-Based 추천 모델을 로드합니다.
        
        Args:
            filepath: Item-Based 모델 pkl 파일 경로
        """
        self.item_based = ItemBasedRecommender.load(filepath)
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
                           n_recommendations: int = 10) -> pd.DataFrame:
        """
        유사한 영화 찾기 (Item-Based CF 사용)
        
        Args:
            movie_id: 기준 영화 ID
            df_movies: 영화 정보 데이터프레임
            n_recommendations: 추천할 영화 개수
            
        Returns:
            유사한 영화 데이터프레임 (similarity 컬럼 포함)
        """
        if self.item_based is None:
            raise ValueError("Item-Based 모델을 먼저 로드해주세요. load_item_based() 실행 필요")
        
        if movie_id not in df_movies['movie_id'].values:
            return pd.DataFrame()
        
        # Item-Based 추천 시스템으로 유사한 영화 찾기
        result_df = self.item_based.recommend(
            movie_id=movie_id,
            top_n=n_recommendations,
            return_scores=True
        )
        
        if result_df is None or result_df.empty:
            return pd.DataFrame()
        
        # 컬럼명 통일 (similarity_score -> similarity)
        result_df = result_df.rename(columns={'similarity_score': 'similarity'})
        
        return result_df
