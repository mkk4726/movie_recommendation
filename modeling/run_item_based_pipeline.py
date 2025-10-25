"""
Item-Based Collaborative Filtering 파이프라인 실행 스크립트
"""
import logging
from pathlib import Path

from models.item_based import ItemBasedRecommender, ItemBasedConfig
from utils.data_integration import DataIntegrator

# Firebase 초기화
from user_system.firebase_config import setup_firebase_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Item-Based CF 파이프라인 실행"""
    
    # 1. YAML 파일에서 설정 로드
    config = ItemBasedConfig.from_yaml()
    
    # 2. 데이터 로드 (config에서 통합 데이터 사용 여부 확인)
    logger.info("\n" + "="*60)
    logger.info("🎬 Item-Based Collaborative Filtering 파이프라인")
    logger.info("="*60)
    
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
    
    # 3. 추천 시스템 초기화 및 학습
    recommender = ItemBasedRecommender(config=config)
    recommender.fit()
    
    # 3. 모델 저장
    save_path = Path(__file__).parent / 'models' / 'pkls' / 'trained_item_based.pkl'
    recommender.save(save_path)
    
    # 4. 추천 테스트
    logger.info("\n" + "="*60)
    logger.info("🎬 추천 테스트")
    logger.info("="*60)
    
    test_movies = ["기생충", "타짜", "범죄도시"]
    
    for movie_title in test_movies:
        logger.info(f"\n\n{'='*60}")
        logger.info(f"📽️  '{movie_title}'와 유사한 영화 추천")
        logger.info("="*60)
        
        recommendations = recommender.recommend_by_title(
            movie_title,
            top_n=5,
            return_scores=True
        )
        
        if recommendations is not None:
            display_cols = ['movie_id', 'title', 'similarity_score']
            print("\n추천 결과:")
            print(recommendations[display_cols].to_string(index=False))
        else:
            logger.warning(f"'{movie_title}' 영화를 찾을 수 없습니다.")
    
    # 5. 모델 로드 테스트
    logger.info("\n\n" + "="*60)
    logger.info("📂 모델 로드 테스트")
    logger.info("="*60)
    
    loaded_recommender = ItemBasedRecommender.load(save_path)
    logger.info("✅ 로드된 모델로 추천 테스트 완료!")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Item-Based CF 파이프라인 완료!")
    logger.info("="*60)
    logger.info(f"\n💾 저장된 모델 위치: {save_path}")
    logger.info("\n사용 예시:")
    logger.info("  from models.item_based import ItemBasedRecommender")
    logger.info(f"  recommender = ItemBasedRecommender.load('{save_path}')")
    logger.info("  recommendations = recommender.recommend_by_title('영화제목', top_n=10)")


if __name__ == "__main__":
    main()

