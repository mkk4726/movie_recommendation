"""
SVD 파이프라인 테스트 스크립트
"""
import logging
import pandas as pd
from pathlib import Path
from models.svd import SVDRecommenderPipeline, ModelConfig

# Firebase 초기화
from user_system.firebase_config import setup_firebase_config
from user_system.firebase_firestore import FirestoreManager

from data_scraping.common.data_loader import load_ratings_data
from utils.data import filter_by_min_counts

# Logger 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🚀 SVD 추천 시스템 파이프라인 테스트")
    
    # YAML 파일에서 모델 설정 로드
    config = ModelConfig.from_yaml()
    
    # 데이터 로드 (config에서 통합 데이터 사용 여부 확인)
    if getattr(config, 'use_integrated_data', True): # 사용할 때 True
        logger.info("📊 Firebase 통합 데이터를 사용합니다...")
        
        # Firebase 초기화
        logger.info("🔥 Firebase를 초기화하는 중...")
        firebase_available = setup_firebase_config()
        if not firebase_available:
            logger.error("❌ Firebase 초기화에 실패했습니다. 기존 데이터를 사용합니다.")
            logger.info("📊 기존 데이터를 사용합니다...")
        else:
            logger.info("✅ Firebase 초기화 완료!")
            firestore_manager = FirestoreManager()
            logger.info("Firebase에서 사용자 상호작용 데이터를 로드하는 중...")
            firebase_data = firestore_manager.get_all_user_ratings()
            logger.info(f"  - Firebase 데이터: {len(firebase_data):,}개 평점")

            logger.info("📥 기존 데이터를 로드하는 중...")
            df_ratings = load_ratings_data()
            logger.info(f"  - 기존 데이터: {len(df_ratings):,}개 평점")
            
            logger.info("🔍 데이터를 필터링하는 중...")
            logger.info(f"  - 필터링 조건: 사용자당 최소 {config.min_user_ratings}개, 영화당 최소 {config.min_movie_ratings}개")            
            filtered_data = filter_by_min_counts(df_ratings, min_movie_ratings=config.min_movie_ratings, min_user_ratings=config.min_user_ratings)
            logger.info(f"  - 필터링된 데이터: {len(filtered_data):,}개 평점")
                       

            logger.info("✅ 통합된 데이터로 설정이 업데이트되었습니다.")
    else:
        logger.info("📊 기존 데이터를 사용합니다...")
        # 기존 데이터만 사용하는 경우
        logger.info("📥 기존 데이터를 로드하는 중...")
        df_ratings = load_ratings_data()
        logger.info(f"  - 기존 데이터: {len(df_ratings):,}개 평점")
        
        logger.info("🔍 데이터를 필터링하는 중...")
        logger.info(f"  - 필터링 조건: 사용자당 최소 {config.min_user_ratings}개, 영화당 최소 {config.min_movie_ratings}개")            
        filtered_data = filter_by_min_counts(df_ratings, min_movie_ratings=config.min_movie_ratings, min_user_ratings=config.min_user_ratings)
        logger.info(f"  - 필터링된 데이터: {len(filtered_data):,}개 평점")
        
        # 빈 Firebase 데이터 생성
        firebase_data = pd.DataFrame(columns=['user_id', 'movie_id', 'rating'])
    
    # 파이프라인 생성 및 전체 실행
    pipeline = SVDRecommenderPipeline(config)
    pipeline.run_full_pipeline(filtered_data=filtered_data, firebase_data=firebase_data)
    
    # 결과 출력
    logger.info("=" * 60)
    logger.info("📊 최종 평가 결과:")
    logger.info(str(pipeline.metrics))
    
    # 모델 저장
    model_dir = Path(__file__).parent / 'models' / 'pkls'
    model_path = model_dir / 'trained_svd_pipeline.pkl'
    pipeline.save_model(str(model_path))
    
    # 모델 로드 테스트
    logger.info("=" * 60)
    logger.info("🔄 모델 로드 테스트...")
    loaded_pipeline = SVDRecommenderPipeline.load_model(str(model_path))
    
    # 추천 테스트
    logger.info("=" * 60)
    logger.info("🎬 추천 테스트...")
    
    from data_scraping.common.data_loader import load_movie_data
    df_movies = load_movie_data()
    
    # 첫 번째 사용자에게 추천
    user_id = loaded_pipeline.df_seen_data['user_id'].iloc[0]
    logger.info(f"사용자 ID: {user_id}")
    
    top_watched, recommendations = loaded_pipeline.recommend_for_user(
        user_id, df_movies, n=5
    )
    
    logger.info("✨ 추천 영화 (예상 평점 높은 순):")
    for idx, row in recommendations.iterrows():
        logger.info(f"{idx+1}. {row.get('title', 'N/A')} (예측 평점: {row['predicted_rating']:.2f})")
        logger.info(f"   장르: {row.get('genre', 'N/A')}, 연도: {row.get('year', 'N/A')}")
    
    logger.info("🎬 자주 본 영화 (높은 평점 순):")
    for idx, row in top_watched.iterrows():
        logger.info(f"{idx+1}. {row.get('title', 'N/A')} (평점: {row['rating']:.1f})")
    
    logger.info("=" * 60)
    logger.info("✅ 모든 테스트 완료!")

if __name__ == "__main__":
    main()

