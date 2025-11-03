"""
Item-Based Collaborative Filtering 파이프라인 실행 스크립트
"""
import logging
import yaml
from pathlib import Path

from models.item_based import ItemBasedRecommender, ItemBasedConfig

from data_scraping.common.data_loader import load_ratings_data
from utils.data import filter_by_min_counts

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Item-Based CF 파이프라인 실행"""
    
    config = ItemBasedConfig.from_yaml()
    
    # 데이터 설정 로드
    data_config_path = Path(__file__).parent / 'utils' / 'data_config.yaml'
    logger.info(f"📄 데이터 설정 파일 로드: {data_config_path}")
    with open(data_config_path, 'r', encoding='utf-8') as f:
        data_config_dict = yaml.safe_load(f)
    
    if 'data' not in data_config_dict:
        raise ValueError("data_config.yaml 파일에 'data' 섹션이 없습니다.")
    
    data_config = data_config_dict['data']
    min_user_ratings = data_config.get('min_user_ratings', 10)
    min_movie_ratings = data_config.get('min_movie_ratings', 30)
    
    logger.info("\n" + "="*60)
    logger.info("🎬 Item-Based Collaborative Filtering 파이프라인")
    logger.info("="*60)
           
    logger.info("📥 데이터를 로드하는 중...")
    df_ratings = load_ratings_data()
    logger.info(f"  - 데이터: {len(df_ratings):,}개 평점")
    
    logger.info("🔍 데이터를 필터링하는 중...")
    logger.info(f"  - 필터링 조건: 사용자당 최소 {min_user_ratings}개, 영화당 최소 {min_movie_ratings}개")            
    filtered_data = filter_by_min_counts(df_ratings, min_movie_ratings=min_movie_ratings, min_user_ratings=min_user_ratings)
    logger.info(f"  - 필터링된 데이터: {len(filtered_data):,}개 평점")
                       
    # 3. 추천 시스템 초기화 및 학습
    recommender = ItemBasedRecommender(config=config)
    recommender.fit(filtered_data)
    
    # 3. 모델 저장
    save_path = Path(__file__).parent / 'models' / 'pkls' / 'trained_item_based.pkl'
    recommender.save(save_path)
    
    # 4. 추천 테스트
    logger.info("\n" + "="*60)
    logger.info("🎬 추천 테스트")
    logger.info("="*60)
    
    # 첫 번째 movie_id로 추천 테스트
    first_movie_id = filtered_data['movie_id'].iloc[0]
    logger.info(f"테스트할 영화 ID: {first_movie_id}")
    
    recommendations = recommender.recommend(
        movie_id=first_movie_id,
        top_n=5,
        return_scores=True
    )
    
    if recommendations is not None:
        display_cols = ['movie_id', 'title', 'similarity_score']
        print("\n추천 결과:")
        print(recommendations[display_cols].to_string(index=False))
    else:
        logger.warning(f"영화 ID '{first_movie_id}'에 대한 추천을 찾을 수 없습니다.")
    
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

