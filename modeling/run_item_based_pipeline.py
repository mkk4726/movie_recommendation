"""
Item-Based Collaborative Filtering 파이프라인 실행 스크립트
"""
import logging
from pathlib import Path

from models.item_based import ItemBasedRecommender, ItemBasedConfig

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
    
    # 2. 추천 시스템 초기화 및 학습
    logger.info("\n" + "="*60)
    logger.info("🎬 Item-Based Collaborative Filtering 파이프라인")
    logger.info("="*60)
    
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

