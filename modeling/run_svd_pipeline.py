"""
SVD 파이프라인 테스트 스크립트
"""
import logging
from pathlib import Path
from models.svd import SVDRecommenderPipeline, ModelConfig
from utils.data_integration import DataIntegrator

# Firebase 초기화
from user_system.firebase_config import setup_firebase_config

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
    if getattr(config, 'use_integrated_data', True): # 사용할 떄 True
        logger.info("📊 Firebase 통합 데이터를 사용합니다...")
        
        # Firebase 초기화
        logger.info("🔥 Firebase를 초기화하는 중...")
        firebase_available = setup_firebase_config()
        if not firebase_available:
            logger.error("❌ Firebase 초기화에 실패했습니다. 기존 데이터를 사용합니다.")
            logger.info("📊 기존 데이터를 사용합니다...")
        else:
            logger.info("✅ Firebase 초기화 완료!")
            integrator = DataIntegrator()
            
            # 1. 기존 데이터 로드
            logger.info("📥 기존 데이터를 로드하는 중...")
            original_data = integrator.load_original_data()
            logger.info(f"  - 기존 데이터: {len(original_data):,}개 평점")
            
            # 2. Firebase 데이터 로드
            logger.info("📥 Firebase 데이터를 로드하는 중...")
            firebase_data = integrator.load_firebase_data()
            logger.info(f"  - Firebase 데이터: {len(firebase_data):,}개 평점")
            
            # 3. 데이터 통합
            logger.info("🔗 데이터를 통합하는 중...")
            integrated_data = integrator.integrate_data(original_data, firebase_data)
            logger.info(f"  - 통합된 데이터: {len(integrated_data):,}개 평점")
            
            # 4. 데이터 필터링 (기존 모델의 필터링 설정 사용)
            logger.info("🔍 데이터를 필터링하는 중...")
            logger.info(f"  - 필터링 조건: 사용자당 최소 {config.min_user_ratings}개, 영화당 최소 {config.min_movie_ratings}개")
            
            filtered_data = integrator.filter_data(
                integrated_data, 
                min_user_ratings=config.min_user_ratings,
                min_movie_ratings=config.min_movie_ratings
            )
            
            # 5. 통계 정보 출력
            stats = integrator.get_data_statistics(filtered_data)
            logger.info("="*60)
            logger.info("📈 Firebase 통합 데이터 통계")
            logger.info("="*60)
            logger.info(f"  - 총 평점 수: {stats['total_ratings']:,}")
            logger.info(f"  - 고유 사용자: {stats['unique_users']:,}")
            logger.info(f"  - 고유 영화: {stats['unique_movies']:,}")
            logger.info(f"  - 평균 평점: {stats['avg_rating']:.2f}")
            
            # 평점 분포 출력
            if stats['rating_distribution']:
                logger.info("  - 평점 분포:")
                for rating, count in sorted(stats['rating_distribution'].items()):
                    logger.info(f"    {rating}점: {count:,}개")
            
            # 통합된 데이터를 config에 설정
            config.df_ratings = filtered_data
            logger.info("✅ 통합된 데이터로 설정이 업데이트되었습니다.")
    else:
        logger.info("📊 기존 데이터를 사용합니다...")
    
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
    user_id = loaded_pipeline.df_filtered['user_id'].iloc[0]
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

