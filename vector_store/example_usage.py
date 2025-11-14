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
        print(f"{i}. index={result['index']} (score: {result['score']:.4f})")


def main():
    """메인 함수"""
    print("\n🎬 Vector Store 사용 예제\n")
    
    try:
        # 1. 인덱스 생성
        example_build_index()
        
        # 2. 검색
        example_search()
        
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

