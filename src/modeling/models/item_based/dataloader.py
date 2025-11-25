"""
Item-Based Collaborative Filtering 데이터 로더
캐시 기능을 포함한 데이터 로드 함수
"""
import hashlib
import yaml
import pandas as pd
from pathlib import Path
from typing import Optional

from data_scraping.common.data_loader import load_ratings_data
from modeling.utils.data import filter_by_min_counts


def load_data(
    refresh: bool = False,
    data_config_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Item-Based CF용 필터링된 데이터 로드 (캐시 지원)
    
    Args:
        refresh: True이면 캐시를 무시하고 새로 생성 (기본값: False)
        data_config_path: 데이터 설정 파일 경로 (None이면 기본 경로 사용)
        
    Returns:
        pd.DataFrame: 필터링된 평점 데이터
    """
    # 기본 설정
    if data_config_path is None:
        data_config_path = Path(__file__).parent.parent.parent / 'utils' / 'data_config.yaml'
    else:
        data_config_path = Path(data_config_path)
    
    print(f"📄 데이터 설정 파일 로드: {data_config_path}")
    with open(data_config_path, 'r', encoding='utf-8') as f:
        data_config_dict = yaml.safe_load(f)
    
    data_config = data_config_dict['data']
    min_user_ratings = data_config.get('min_user_ratings', 10)
    min_movie_ratings = data_config.get('min_movie_ratings', 30)
    
    # 캐시 디렉토리 설정 (dataloader.py와 같은 위치)
    cache_dir = Path(__file__).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 캐시 키 생성 (data_config 기반)
    cache_key = f"{min_user_ratings}_{min_movie_ratings}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
    cache_path = cache_dir / f"cache_item_based_{cache_hash}.csv"
    
    # 캐시에서 로드 시도 (refresh=False이고 파일이 존재하는 경우)
    if not refresh and cache_path.exists():
        print(f"\n✅ 캐시에서 데이터 로드: {cache_path.name}")
        filtered_data = pd.read_csv(cache_path, dtype={'user_id': str, 'movie_id': str})
        print(f"  - 캐시된 데이터: {len(filtered_data):,}개 평점\n")
        return filtered_data
    
    # 새로 생성
    print("\n" + "="*60)
    print("🎬 Item-Based Collaborative Filtering 파이프라인")
    print("="*60)
    
    print("📥 데이터를 로드하는 중...")
    df_ratings = load_ratings_data(verbose=True)
    print(f"  - 데이터: {len(df_ratings):,}개 평점")
    
    print("🔍 데이터를 필터링하는 중...")
    print(f"  - 필터링 조건: 사용자당 최소 {min_user_ratings}개, 영화당 최소 {min_movie_ratings}개")
    filtered_data = filter_by_min_counts(
        df_ratings, 
        min_movie_ratings=min_movie_ratings, 
        min_user_ratings=min_user_ratings
    )
    print(f"  - 필터링된 데이터: {len(filtered_data):,}개 평점")
    
    # 캐시에 저장
    print("\n💾 캐시 파일 저장 중...")
    filtered_data.to_csv(cache_path, index=False)
    print(f"✅ 캐시 저장 완료: {cache_path.name}\n")
    
    return filtered_data
