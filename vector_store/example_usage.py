"""
Vector Store 사용 예제

FAISS 인덱스 생성 및 검색 예제
"""

import numpy as np
from pathlib import Path

# 1. 인덱스 생성 예제
def example_build_index():
    """인덱스 생성 예제"""
    from vector_store.build_index import IndexBuilder
    from vector_store import load_config
    
    print("=" * 60)
    print("1. 인덱스 생성 예제")
    print("=" * 60)
    
    # 설정 로드
    config = load_config()
    
    # 빌더 초기화
    builder = IndexBuilder(
        vector_dim=config['vector']['dim'],
        distance_metric=config['vector']['distance_metric']
    )
    
    # 더미 데이터 추가
    print("\n더미 데이터 생성 중...")
    for i in range(100):
        # 랜덤 벡터 생성 (실제로는 CLIP 모델 사용)
        embedding = np.random.randn(512).astype('float32')
        
        builder.add_item(
            embedding=embedding,
            movie_id=i,
            title=f"Movie {i}",
            genres=["Action", "Drama"] if i % 2 == 0 else ["Comedy", "Romance"],
            year=2015 + (i % 10),
            poster_url=f"https://example.com/poster_{i}.jpg",
            rating=3.0 + (i % 5) * 0.5
        )
    
    # 인덱스 저장
    output_dir = Path(config['index']['base_dir'])
    print(f"\n인덱스 저장 중: {output_dir}")
    builder.save(
        output_dir=output_dir,
        save_embeddings=config['build']['save_embeddings']
    )
    
    print("\n✅ 인덱스 생성 완료!")


# 2. 검색 예제
def example_search():
    """검색 예제"""
    from vector_store import FAISSManager
    
    print("\n" + "=" * 60)
    print("2. 검색 예제")
    print("=" * 60)
    
    # 매니저 초기화
    print("\n인덱스 로드 중...")
    manager = FAISSManager()
    manager.load()
    
    print(f"✅ 로드 완료: {manager.total_vectors}개 벡터")
    
    # 랜덤 쿼리 벡터 생성
    query_vector = np.random.randn(512).astype('float32')
    
    # 기본 검색
    print("\n--- 기본 검색 (top 5) ---")
    results = manager.search(query_vector, k=5)
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']} (score: {result['score']:.4f})")
    
    # 필터링 검색 - 장르
    print("\n--- 장르 필터링 (Action) ---")
    results = manager.search(
        query_vector,
        k=5,
        filters={"genres": ["Action"]}
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']} - {result['genres']} (score: {result['score']:.4f})")
    
    # 필터링 검색 - 연도
    print("\n--- 연도 필터링 (2020-2024) ---")
    results = manager.search(
        query_vector,
        k=5,
        filters={"year_min": 2020, "year_max": 2024}
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']} ({result['year']}) (score: {result['score']:.4f})")
    
    # 복합 필터링
    print("\n--- 복합 필터링 (Comedy + 2018 이후 + 평점 4.0 이상) ---")
    results = manager.search(
        query_vector,
        k=5,
        filters={
            "genres": ["Comedy"],
            "year_min": 2018,
            "rating_min": 4.0
        }
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']} ({result['year']}) - "
              f"Rating: {result.get('rating', 'N/A')} (score: {result['score']:.4f})")


# 3. 영화 ID로 유사 영화 찾기
def example_search_by_id():
    """영화 ID로 유사 영화 찾기 예제"""
    from vector_store import FAISSManager
    
    print("\n" + "=" * 60)
    print("3. 영화 ID로 유사 영화 찾기")
    print("=" * 60)
    
    manager = FAISSManager()
    manager.load()
    
    # 특정 영화와 유사한 영화 찾기
    movie_id = 10
    print(f"\n'{movie_id}' 영화와 유사한 영화 찾기...")
    
    # 원본 영화 정보
    original = manager.get_metadata_by_movie_id(movie_id)
    if original:
        print(f"\n원본: {original['title']} ({original['year']}) - {original['genres']}")
    
    # 유사 영화 검색
    similar_movies = manager.search_by_id(movie_id, k=5)
    
    print("\n유사한 영화:")
    for i, movie in enumerate(similar_movies, 1):
        print(f"{i}. {movie['title']} ({movie['year']}) - "
              f"{movie['genres']} (score: {movie['score']:.4f})")


# 4. 메타데이터 조회
def example_metadata():
    """메타데이터 조회 예제"""
    from vector_store import FAISSManager
    
    print("\n" + "=" * 60)
    print("4. 메타데이터 조회")
    print("=" * 60)
    
    manager = FAISSManager()
    manager.load()
    
    # 인덱스로 조회
    print("\n--- 인덱스로 조회 (idx=0) ---")
    meta = manager.get_metadata(0)
    if meta:
        for key, value in meta.items():
            print(f"  {key}: {value}")
    
    # 영화 ID로 조회
    print("\n--- 영화 ID로 조회 (movie_id=5) ---")
    meta = manager.get_metadata_by_movie_id(5)
    if meta:
        for key, value in meta.items():
            print(f"  {key}: {value}")


def main():
    """메인 함수"""
    print("\n🎬 Vector Store 사용 예제\n")
    
    try:
        # 1. 인덱스 생성
        example_build_index()
        
        # 2. 검색
        example_search()
        
        # 3. 영화 ID로 유사 영화 찾기
        example_search_by_id()
        
        # 4. 메타데이터 조회
        example_metadata()
        
        print("\n" + "=" * 60)
        print("✅ 모든 예제 완료!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n❌ 오류: {e}")
        print("\n먼저 인덱스를 생성하세요:")
        print("  python -m vector_store.build_index")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

