"""
로컬에서 모델을 학습하고 저장하는 스크립트
"""
import sys
from pathlib import Path
import pickle
import numpy as np

# 경로 추가
sys.path.append(str(Path(__file__).parent))

from utils.data_loader import load_movie_data, load_ratings_data, filter_data
from utils.recommender_lite import MovieRecommenderLite

def main():
    print("📊 데이터 로딩 중...")
    df_movies = load_movie_data()
    df_ratings = load_ratings_data()
    df_ratings_filtered = filter_data(df_ratings, min_user_ratings=30, min_movie_ratings=10)
    
    print(f"영화 수: {len(df_movies)}")
    print(f"평점 수: {len(df_ratings_filtered)}")
    print(f"사용자 수: {df_ratings_filtered['user_id'].nunique()}")
    
    print("\n🤖 추천 시스템 학습 중 (경량화 버전)...")
    recommender = MovieRecommenderLite()
    
    print("  - 협업 필터링 학습 중...")
    recommender.train_collaborative_filtering(df_ratings_filtered, n_factors=50)
    
    print("  - 컨텐츠 기반 학습 중...")
    recommender.train_content_based(df_movies)
    
    # 모델 저장
    model_dir = Path(__file__).parent / 'models'
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / 'recommender_model.pkl'
    
    print(f"\n💾 모델 저장 중: {model_path}")
    with open(model_path, 'wb') as f:
        pickle.dump(recommender, f)
    
    # 파일 크기 확인
    size_mb = model_path.stat().st_size / (1024 * 1024)
    print(f"✅ 모델 저장 완료! (크기: {size_mb:.2f} MB)")
    
    print("\n✨ 다음 단계:")
    print("1. 모델 파일이 너무 크면 Git LFS 사용")
    print("2. GitHub에 푸시")
    print("3. Streamlit Cloud 재배포")

if __name__ == "__main__":
    main()

