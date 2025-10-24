"""
SVD 파이프라인 테스트 스크립트
"""
import logging
from pathlib import Path
from models.svd import SVDRecommenderPipeline, ModelConfig

# Logger 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 SVD 추천 시스템 파이프라인 테스트")
    
    # 모델 설정 (테스트용으로 작은 파라미터 사용)
    config = ModelConfig(
        n_factors=20,  # 빠른 학습을 위해 축소
        n_epochs=10,   # 빠른 학습을 위해 축소
        lr_all=0.005,
        reg_all=0.02,
        test_size=0.2,
        min_user_ratings=30,
        min_movie_ratings=10,
        verbose=True
    )
    
    # 파이프라인 생성 및 전체 실행
    pipeline = SVDRecommenderPipeline(config)
    metrics = pipeline.run_full_pipeline()
    
    # 결과 출력
    logger.info("=" * 60)
    logger.info("📊 최종 평가 결과:")
    logger.info(str(metrics))
    
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
    user_id = loaded_pipeline.df_preprocessed['user_id'].iloc[0]
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
        logger.info(f"{idx+1}. {row['movie_title']} (평점: {row['rating']:.1f})")
    
    logger.info("=" * 60)
    logger.info("✅ 모든 테스트 완료!")

if __name__ == "__main__":
    main()

