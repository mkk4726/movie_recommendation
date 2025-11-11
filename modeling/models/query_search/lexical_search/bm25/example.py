"""
BM25 영화 검색 사용 예시

이 파일은 BM25 모듈의 사용법을 보여줍니다.
"""
import logging
import pandas as pd
from pathlib import Path

from .config import BM25Config
from .movie_search import MovieBM25


def main():
    """BM25 영화 검색 시스템 테스트"""
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("BM25 영화 검색 시스템 테스트")
    print("=" * 80)
    
    # 1. 설정 로드
    print("\n[1] 설정 로드")
    config = BM25Config.from_yaml()
    print(f"  - k1: {config.k1}")
    print(f"  - b: {config.b}")
    print(f"  - top_k: {config.top_k}")
    print(f"  - 필드 가중치: {config.field_weights}")
    
    # 2. 영화 데이터 로드
    print("\n[2] 영화 데이터 로드")
    movies_path = Path(__file__).parent.parent.parent.parent.parent.parent / "data_scraping" / "data" / "ml-32m" / "movies.csv"
    
    if not movies_path.exists():
        print(f"  ⚠️ 영화 데이터 파일을 찾을 수 없습니다: {movies_path}")
        print("  샘플 데이터로 테스트를 진행합니다.")
        
        # 샘플 데이터 생성
        movies_df = pd.DataFrame({
            'movieId': [1, 2, 3, 4, 5],
            'title': [
                'Toy Story (1995)',
                'Jumanji (1995)',
                'Grumpier Old Men (1995)',
                'Waiting to Exhale (1995)',
                'Father of the Bride Part II (1995)'
            ],
            'genres': [
                'Adventure|Animation|Children|Comedy|Fantasy',
                'Adventure|Children|Fantasy',
                'Comedy|Romance',
                'Comedy|Drama|Romance',
                'Comedy'
            ]
        })
    else:
        movies_df = pd.read_csv(movies_path)
        print(f"  ✓ {len(movies_df)}개 영화 로드 완료")
    
    # 3. BM25 색인 생성
    print("\n[3] BM25 색인 생성")
    movie_bm25 = MovieBM25(config=config)
    movie_bm25.fit(movies_df)
    
    # 4. 검색 테스트
    print("\n[4] 검색 테스트")
    test_queries = [
        "toy story",
        "adventure fantasy",
        "comedy romance",
        "animation children"
    ]
    
    for query in test_queries:
        print(f"\n  쿼리: '{query}'")
        results = movie_bm25.search(query, top_k=5)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"    {i}. {result}")
        else:
            print("    검색 결과 없음")
    
    # 5. 색인 저장/로드 테스트
    print("\n[5] 색인 저장/로드 테스트")
    cache_dir = Path(__file__).parent / "cache"
    movie_bm25.save(str(cache_dir))
    print(f"  ✓ 색인 저장 완료: {cache_dir}")
    
    # 로드 테스트
    loaded_bm25 = MovieBM25.load(str(cache_dir))
    print(f"  ✓ 색인 로드 완료")
    
    # 로드된 색인으로 검색
    print(f"\n  로드된 색인으로 검색: 'toy story'")
    results = loaded_bm25.search("toy story", top_k=3)
    for i, result in enumerate(results, 1):
        print(f"    {i}. {result}")
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()

