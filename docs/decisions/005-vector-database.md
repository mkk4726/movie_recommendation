# ADR 005: 벡터 데이터베이스 선택 - FAISS

## 상태
✅ Accepted

## 날짜
2025-11-14

## 컨텍스트
포스터 이미지 기반 영화 검색 기능(`poster_vibe_search`)을 구현하기 위해 이미지 임베딩 벡터를 저장하고 유사도 검색을 수행할 벡터 저장소가 필요했다. 약 8만개의 영화 포스터 벡터를 저장하고 실시간으로 유사도 검색을 제공해야 한다.

### 요구사항
- 이미지 임베딩 벡터 저장 (CLIP 모델, 512차원)
- 빠른 유사도 검색 (ANN - Approximate Nearest Neighbor)
- 영화 메타데이터 함께 관리 (제목, 장르, 연도, 포스터 URL 등)
- 메타데이터 기반 필터링 (장르별, 연도별 검색)
- **서버(GPU)에서 임베딩 생성 → 로컬에서 사용하는 워크플로우**
- 구글 드라이브를 통한 파일 공유 및 버전 관리

### 고려한 옵션

1. **FAISS (Facebook AI Similarity Search)**
   - 장점:
     - 가장 빠른 순수 벡터 검색 속도 (~0.5-1ms for 80K vectors)
     - Meta에서 개발한 검증된 라이브러리
     - 다양한 인덱스 타입 제공 (Flat, IVF, HNSW, PQ 등)
     - **단일 파일로 저장 가능** (~160MB for 80K×512 vectors)
     - 메모리 효율적
     - 완전 무료 오픈소스 (MIT 라이센스)
     - **구글 드라이브 공유에 최적** (파일 2개만 업로드)
     - 버전 관리 용이 (파일명에 날짜 추가)
   - 단점:
     - 메타데이터 관리 불편 (별도 JSON/pickle 파일 필요)
     - 벡터 업데이트/삭제 어려움 (인덱스 재구축 필요)
     - 필터링 기능 없음 (직접 구현 필요, 하지만 8만개는 충분히 빠름)

2. **Qdrant**
   - 장점:
     - HNSW 알고리즘으로 빠른 ANN 검색
     - 벡터와 메타데이터 통합 관리
     - 강력한 필터링 기능 (payload 기반)
     - 실시간 벡터 추가/업데이트 가능
     - 깔끔한 Python API
   - 단점:
     - **복잡한 폴더 구조** (수십개 파일, segments/snapshots)
     - 구글 드라이브 공유 시 압축 필요
     - 버전 관리 복잡
     - Qdrant 서버 필요 (로컬 모드도 초기화 시간 필요)
     - 용량 더 큼 (~200-300MB)

3. **ChromaDB**
   - 장점:
     - 간단한 API
     - 메타데이터 필터링 우수
   - 단점:
     - Qdrant와 유사한 파일 구조 문제
     - 대용량 데이터에서 느림

## 결정
**FAISS를 벡터 저장소로 선택한다.**

### 선택 이유

1. **워크플로우에 최적화**
   - 서버(GPU)에서 한번 임베딩 생성 및 인덱스 구축
   - 단일 파일(`.index`)로 저장 → 구글 드라이브 업로드
   - 로컬에서 다운로드 → 즉시 사용 (서버 불필요)
   - 재학습 시 새 버전 파일만 업로드

2. **파일 관리 용이성**
   ```
   구글 드라이브:
   ├── movie_posters_20251114.index  (~160MB)
   ├── metadata_20251114.json        (~5MB)
   └── embeddings_20251114.npy       (~160MB, 백업용)
   ```
   - 파일 2-3개로 완전한 시스템 구성
   - 버전별 관리 쉬움 (날짜 suffix)
   - 팀원과 공유 간편

3. **최고의 검색 성능**
   - 8만개 벡터: ~0.5-1ms (순수 검색)
   - 메타데이터 필터링 직접 구현해도 충분히 빠름
   - 네트워크 지연(~50-100ms)이 훨씬 더 큼

4. **실용적 선택**
   - 8만개 규모에서는 실시간 업데이트 불필요
   - 포스터 데이터는 정적 (자주 변경 안됨)
   - 업데이트 시 서버에서 재구축 후 새 파일 배포

5. **단순성**
   - 별도 서버/Docker 불필요
   - 의존성 최소화 (`pip install faiss-cpu`)
   - 디버깅 쉬움 (단순 파일 I/O)

## 구현 세부사항

### 아키텍처
```
vector_store/
├── __init__.py
├── faiss_manager.py       # FAISS 인덱스 관리 클래스
├── config.py              # 설정 (인덱스 경로, 차원 등)
└── indices/               # FAISS 인덱스 파일 저장 (gitignore)
    ├── movie_posters.index
    ├── metadata.json
    └── embeddings.npy     # 백업용 (선택)
```

### 워크플로우

#### 1️⃣ 서버(GPU)에서 인덱스 생성
```python
# modeling/models/poster_vibe_search/build_index.py
import faiss
import numpy as np
from tqdm import tqdm

# CLIP으로 이미지 임베딩 생성
embeddings = []
metadata = []

for movie in tqdm(movies):
    img_emb = clip_model.encode_image(movie.poster)  # GPU
    embeddings.append(img_emb)
    metadata.append({
        "movie_id": movie.id,
        "title": movie.title,
        "genres": movie.genres,
        "year": movie.year,
        "poster_url": movie.poster_url
    })

# NumPy 배열로 변환
embeddings = np.vstack(embeddings).astype('float32')  # (80000, 512)

# L2 정규화 (Cosine similarity를 위해)
faiss.normalize_L2(embeddings)

# FAISS 인덱스 생성
index = faiss.IndexFlatIP(512)  # Inner Product (정규화 후 = Cosine)
index.add(embeddings)

# 저장
faiss.write_index(index, "movie_posters.index")
np.save("embeddings.npy", embeddings)  # 백업

import json
with open("metadata.json", "w") as f:
    json.dump(metadata, f)

# 구글 드라이브에 업로드
```

#### 2️⃣ 로컬에서 사용
```python
# vector_store/faiss_manager.py
import faiss
import numpy as np
import json

class FAISSManager:
    def __init__(self, index_path, metadata_path):
        self.index = faiss.read_index(index_path)
        with open(metadata_path) as f:
            self.metadata = json.load(f)
    
    def search(self, query_vector, k=10, filters=None):
        """유사도 검색 + 필터링"""
        # 정규화
        query_vector = query_vector.astype('float32')
        faiss.normalize_L2(query_vector.reshape(1, -1))
        
        # 검색 (필터링 고려해서 더 많이 가져옴)
        search_k = k * 10 if filters else k
        scores, indices = self.index.search(query_vector.reshape(1, -1), search_k)
        
        # 결과 구성 + 필터링
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:  # FAISS에서 결과 없음
                continue
            
            meta = self.metadata[int(idx)]
            
            # 필터 적용
            if filters:
                if not self._apply_filters(meta, filters):
                    continue
            
            results.append({
                "movie_id": meta["movie_id"],
                "title": meta["title"],
                "score": float(score),
                **meta
            })
            
            if len(results) >= k:
                break
        
        return results
    
    def _apply_filters(self, meta, filters):
        """메타데이터 필터링"""
        if "genres" in filters:
            if not any(g in meta["genres"] for g in filters["genres"]):
                return False
        
        if "year_min" in filters and meta["year"] < filters["year_min"]:
            return False
        
        if "year_max" in filters and meta["year"] > filters["year_max"]:
            return False
        
        return True
```

### 기술 스택
- **FAISS**: `faiss-cpu` (로컬), `faiss-gpu` (서버)
- **벡터 차원**: 512 (CLIP ViT-B/32)
- **거리 메트릭**: Cosine Similarity (Inner Product with L2 normalization)
- **인덱스 타입**: IndexFlatIP (정확한 검색, 8만개는 충분히 빠름)

### 주요 기능
1. ✅ 포스터 이미지 벡터 저장 (서버)
2. ✅ 유사도 기반 검색 (로컬, ~0.5-1ms)
3. ✅ 메타데이터 필터링 (장르, 연도 등, Python으로 구현)
4. ✅ 단일 파일 관리 (`.index`, `.json`)
5. ✅ 버전 관리 (파일명에 날짜)

### 성능 (8만 벡터 기준)
- **검색 속도**: ~0.5-1ms (순수 벡터 검색)
- **필터링 포함**: ~2-5ms (Python 필터링)
- **메모리 사용**: ~160MB (인덱스) + ~5MB (메타데이터)
- **인덱싱 시간**: ~1-2분 (서버에서 한번만)
- **파일 크기**: ~165MB (드라이브 업로드)

## 결과
- `vector_store/` - FAISS 벡터 인덱스 관리 모듈
- `modeling/models/poster_vibe_search/` - 포스터 기반 검색 구현
- `modeling/models/poster_vibe_search/build_index.py` - 서버에서 인덱스 생성 스크립트

## 트레이드오프 분석

### FAISS의 제약사항과 해결책

| 제약사항 | 영향 | 해결책 |
|---------|------|--------|
| 메타데이터 별도 관리 | 파일 2개 필요 | JSON 파일로 간단히 관리, 오히려 디버깅 쉬움 |
| 필터링 직접 구현 | 코드 추가 | 8만개는 Python으로도 충분히 빠름 (~ms) |
| 실시간 업데이트 불가 | 재구축 필요 | 포스터 데이터는 정적, 업데이트 빈도 낮음 |
| 인덱스 재구축 시간 | ~1-2분 소요 | 서버에서 한번만, 로컬은 다운로드만 |

### Qdrant/ChromaDB를 선택하지 않은 이유

**Qdrant:**
- ✅ 장점: 통합 관리, 실시간 업데이트, 내장 필터링
- ❌ 단점: 복잡한 파일 구조, 드라이브 공유 불편, 서버 필요
- 💭 판단: 우리 워크플로우(서버→드라이브→로컬)에 맞지 않음

**ChromaDB:**
- ✅ 장점: 간단한 API
- ❌ 단점: Qdrant와 유사한 파일 구조 문제, 성능 낮음
- 💭 판단: FAISS 대비 이점 없음

## 향후 개선 방향

### 단기 (1-2개월)
- [ ] FAISS 인덱스 생성 스크립트 작성
- [ ] 메타데이터 필터링 최적화
- [ ] 구글 드라이브 자동 동기화 스크립트

### 중기 (3-6개월)
- [ ] IVF 인덱스로 업그레이드 (데이터 증가 시)
- [ ] 쿼리 텍스트 임베딩 벡터 추가 (멀티모달 검색)
- [ ] 사용자별 선호도 벡터 저장

### 장기 (6개월+)
- [ ] 하이브리드 검색 (FAISS 벡터 + BM25 텍스트)
- [ ] Product Quantization으로 메모리 최적화
- [ ] A/B 테스트로 검색 품질 개선

### 확장 시나리오
- **데이터 10배 증가 (80만개)**: IVF 인덱스로 전환
- **실시간 업데이트 필요**: Qdrant로 마이그레이션 고려
- **멀티모달 검색**: 텍스트/이미지 벡터 별도 인덱스

## 참고 자료
- [FAISS 공식 문서](https://github.com/facebookresearch/faiss/wiki)
- [FAISS 튜토리얼](https://github.com/facebookresearch/faiss/wiki/Getting-started)
- [Cosine Similarity with FAISS](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)
- `modeling/models/poster_vibe_search/`

## 관련 결정
- [ADR 004: 검색 시스템](./004-search-system.md) - BM25 텍스트 검색과 보완 관계
- [ADR 003: 데이터베이스 선택](./003-database-choice.md) - Firebase와 역할 분리
- [ADR 001: 데이터 소스 선택](./001-data-source-selection.md) - MovieLens 32M 데이터

