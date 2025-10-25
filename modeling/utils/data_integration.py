"""
데이터 통합 모듈
Firebase 사용자 상호작용 데이터와 기존 평점 데이터를 통합
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
import logging
from pathlib import Path
import sys

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

from data_scraping.common.data_loader import load_ratings_data, load_movie_data
from user_system.firebase_firestore import FirestoreManager

# Logger 설정
logger = logging.getLogger(__name__)


class DataIntegrator:
    """데이터 통합 클래스"""
    
    def __init__(self):
        self.firestore_manager = FirestoreManager()
    
    def load_firebase_data(self) -> pd.DataFrame:
        """Firebase에서 사용자 상호작용 데이터 로드"""
        try:
            logger.info("Firebase에서 사용자 상호작용 데이터를 로드하는 중...")
            firebase_data = self.firestore_manager.get_all_user_ratings()
            
            if firebase_data.empty:
                logger.warning("Firebase에서 데이터를 찾을 수 없습니다.")
                return pd.DataFrame()
            
            # 데이터 정리
            firebase_data = firebase_data.dropna(subset=['user_id', 'movie_id', 'rating'])
            firebase_data = firebase_data[firebase_data['rating'] >= 0.5]
            firebase_data = firebase_data[firebase_data['rating'] <= 5.0]
            
            logger.info(f"Firebase에서 {len(firebase_data)}개의 평점 데이터를 로드했습니다.")
            return firebase_data
            
        except Exception as e:
            logger.error(f"Firebase 데이터 로드 중 오류: {e}")
            return pd.DataFrame()
    
    def load_original_data(self) -> pd.DataFrame:
        """기존 평점 데이터 로드"""
        try:
            logger.info("기존 평점 데이터를 로드하는 중...")
            original_data = load_ratings_data()
            logger.info(f"기존 데이터에서 {len(original_data)}개의 평점 데이터를 로드했습니다.")
            return original_data
            
        except Exception as e:
            logger.error(f"기존 데이터 로드 중 오류: {e}")
            return pd.DataFrame()
    
    def integrate_data(self, 
                      original_data: pd.DataFrame,
                      firebase_data: pd.DataFrame
                      ):
        """
        기존 데이터와 Firebase 데이터를 통합
        
        Args:
            original_data: 기존 평점 데이터
            movie_info: pd.DataFrame
            firebase_data: Firebase 평점 데이터
        
        Returns:
            통합된 평점 데이터
        """
        try:
            logger.info("데이터 통합을 시작합니다...")
            
            if original_data.empty and firebase_data.empty:
                logger.warning("통합할 데이터가 없습니다.")
                return pd.DataFrame()
            
            # Firebase 데이터가 없는 경우
            if firebase_data.empty:
                logger.info("Firebase 데이터가 없어 기존 데이터만 사용합니다.")
                return original_data.copy()
            
            # 기존 데이터가 없는 경우
            if original_data.empty:
                logger.info("기존 데이터가 없어 Firebase 데이터만 사용합니다.")
                return firebase_data.copy()

            # 데이터 통합
            integrated_data = pd.concat([original_data, firebase_data], ignore_index=True)
            
            # 중복 제거 (동일한 user_id, movie_id 조합)
            before_dedup = len(integrated_data)
            integrated_data = integrated_data.drop_duplicates(subset=['user_id', 'movie_id'], keep='last')
            after_dedup = len(integrated_data)
            
            if before_dedup != after_dedup:
                logger.info(f"중복 제거: {before_dedup - after_dedup}개 제거됨")
            
            logger.info(f"데이터 통합 완료: {len(integrated_data)}개 평점")
            return integrated_data
            
        except Exception as e:
            logger.error(f"데이터 통합 중 오류: {e}")
            return pd.DataFrame()
    
    def get_data_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """데이터 통계 정보 반환"""
        if data.empty:
            return {
                'total_ratings': 0,
                'unique_users': 0,
                'unique_movies': 0,
                'avg_rating': 0.0,
                'rating_distribution': {}
            }
        
        stats = {
            'total_ratings': len(data),
            'unique_users': data['user_id'].nunique(),
            'unique_movies': data['movie_id'].nunique(),
            'avg_rating': data['rating'].mean(),
            'rating_distribution': data['rating'].value_counts().sort_index().to_dict()
        }
        
        return stats
    
    def filter_data(self, 
                   data: pd.DataFrame, 
                   min_user_ratings: int = 10, 
                   min_movie_ratings: int = 5) -> pd.DataFrame:
        """데이터 필터링 (최소 평점 수 기준)"""
        try:
            logger.info(f"데이터 필터링 시작: 최소 사용자 평점 {min_user_ratings}개, 최소 영화 평점 {min_movie_ratings}개")
            
            original_len = len(data)
            
            # 사용자별 평점 수 계산
            user_rating_counts = data['user_id'].value_counts()
            valid_users = user_rating_counts[user_rating_counts >= min_user_ratings].index
            
            # 영화별 평점 수 계산
            movie_rating_counts = data['movie_id'].value_counts()
            valid_movies = movie_rating_counts[movie_rating_counts >= min_movie_ratings].index
            
            # 필터링 적용
            filtered_data = data[
                (data['user_id'].isin(valid_users)) & 
                (data['movie_id'].isin(valid_movies))
            ].copy()
            
            logger.info(f"필터링 완료: {original_len} → {len(filtered_data)}개 평점")
            logger.info(f"유효한 사용자: {len(valid_users)}명, 유효한 영화: {len(valid_movies)}개")
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"데이터 필터링 중 오류: {e}")
            return data
    
    def save_integrated_data(self, 
                           data: pd.DataFrame, 
                           output_path: str,
                           format: str = 'csv') -> bool:
        """통합된 데이터를 파일로 저장"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == 'csv':
                data.to_csv(output_path, index=False)
            elif format.lower() == 'parquet':
                data.to_parquet(output_path, index=False)
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")
            
            logger.info(f"통합된 데이터를 {output_path}에 저장했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"데이터 저장 중 오류: {e}")
            return False
    
    def run_full_integration(self, 
                           output_path: Optional[str] = None,
                           min_user_ratings: int = 10,
                           min_movie_ratings: int = 5) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """전체 데이터 통합 프로세스 실행"""
        try:
            logger.info("전체 데이터 통합 프로세스를 시작합니다...")
            
            # 1. 기존 데이터 로드
            original_data = self.load_original_data()
            
            # 2. Firebase 데이터 로드
            firebase_data = self.load_firebase_data()
            
            # 3. 데이터 통합
            integrated_data = self.integrate_data(original_data, firebase_data)
            
            if integrated_data.empty:
                logger.warning("통합된 데이터가 없습니다.")
                return pd.DataFrame(), {}
            
            # 4. 데이터 필터링
            filtered_data = self.filter_data(integrated_data, min_user_ratings, min_movie_ratings)
            
            # 5. 통계 정보 생성
            stats = self.get_data_statistics(filtered_data)
            
            # 6. 데이터 저장 (경로가 제공된 경우)
            if output_path:
                self.save_integrated_data(filtered_data, output_path)
            
            logger.info("데이터 통합 프로세스가 완료되었습니다.")
            return filtered_data, stats
            
        except Exception as e:
            logger.error(f"데이터 통합 프로세스 중 오류: {e}")
            return pd.DataFrame(), {}


def main():
    """데이터 통합 실행"""
    integrator = DataIntegrator()
    
    # 통합 실행
    integrated_data, stats = integrator.run_full_integration(
        output_path="data/integrated_ratings.csv",
        min_user_ratings=10,
        min_movie_ratings=5
    )
    
    if not integrated_data.empty:
        print("데이터 통합 완료!")
        print(f"통계: {stats}")
    else:
        print("데이터 통합 실패")


if __name__ == "__main__":
    main()
