# Vector Store

FAISS 기반 벡터 저장소 및 유사도 검색 모듈

## 📁 구조

```
vector_store/
├── __init__.py           # 모듈 초기화
├── config.yaml           # 설정 파일
├── config.py             # 설정 로더
├── faiss_manager.py      # FAISS 인덱스 관리
├── build_index.py        # 인덱스 생성 스크립트 (서버용)
├── indices/              # 인덱스 파일 저장 (gitignore)
│   ├── movie_posters.index
│   ├── metadata.json
│   └── embeddings.npy
└── README.md
```

## 🚀 빠른 시작

### 1. 설치

```bash
pip install faiss-cpu  # CPU 버전
# 또는
pip install faiss-gpu  # GPU 버전 (서버)
```

### 2. 인덱스 생성 (서버에서)

```python
from vector_store.build_index import IndexBuilder
import numpy as np

# 빌더 초기화
builder = IndexBuilder(vector_dim=512, distance_metric="cosine")

# 데이터 추가
for movie in movies:
    embedding = clip_model.encode_image(movie.poster)  # CLIP으로 임베딩 생성
    builder.add_item(
        embedding=embedding,
        movie_id=movie.id,
        title=movie.title,
        genres=movie.genres,
        year=movie.year,
        poster_url=movie.poster_url
    )

# 인덱스 저장
builder.save(output_dir="./indices", save_embeddings=True)
```

### 3. 검색 (로컬에서)

```python
from vector_store import FAISSManager

# 매니저 초기화 (기본 설정 사용)
manager = FAISSManager()
manager.load()

# 또는 커스텀 경로 사용
manager = FAISSManager(
    index_path="./indices/movie_posters.index",
    metadata_path="./indices/metadata.json"
)
manager.load()

# 유사도 검색
query_vector = clip_model.encode_image(query_image)
results = manager.search(query_vector, k=10)

for result in results:
    print(f"{result['title']} (score: {result['score']:.3f})")
```

## 📖 사용 예시

### 기본 검색

```python
# 벡터로 검색
results = manager.search(query_vector, k=10)
```

### 필터링 검색

```python
# 장르 필터
results = manager.search(
    query_vector,
    k=10,
    filters={"genres": ["Action", "Sci-Fi"]}
)

# 연도 필터
results = manager.search(
    query_vector,
    k=10,
    filters={"year_min": 2010, "year_max": 2020}
)

# 복합 필터
results = manager.search(
    query_vector,
    k=10,
    filters={
        "genres": ["Drama"],
        "year_min": 2015,
        "rating_min": 4.0
    }
)
```

### 영화 ID로 유사 영화 찾기

```python
# 특정 영화와 유사한 영화 검색
similar_movies = manager.search_by_id(movie_id=1234, k=10)
```

### 메타데이터 조회

```python
# 인덱스로 조회
metadata = manager.get_metadata(idx=0)

# 영화 ID로 조회
metadata = manager.get_metadata_by_movie_id(movie_id=1234)
```

## 🔧 설정

### config.yaml

```yaml
# 인덱스 파일 경로
index:
  base_dir: "vector_store/indices"
  index_file: "movie_posters.index"
  metadata_file: "metadata.json"
  embeddings_file: "embeddings.npy"

# 벡터 설정
vector:
  dim: 512  # CLIP 벡터 차원
  distance_metric: "cosine"  # cosine, l2, ip

# 검색 설정
search:
  default_k: 10  # 기본 검색 결과 수
  search_multiplier: 10  # 필터링 시 추가 검색 배수

# 빌드 설정
build:
  save_embeddings: true  # 임베딩 원본 저장 여부
  save_versioned: true   # 버전별 파일 저장 여부
```

### 설정 로드

```python
from vector_store import load_config

# 기본 설정 로드
config = load_config()

# 커스텀 설정 파일 사용
config = load_config("path/to/custom_config.yaml")

# 특정 경로 가져오기
from vector_store import get_index_path, get_metadata_path

index_path = get_index_path(config)
metadata_path = get_metadata_path(config)
```

## 📊 성능

- **검색 속도**: ~0.5-1ms (8만 벡터 기준)
- **필터링 포함**: ~2-5ms
- **메모리 사용**: ~160MB (인덱스) + ~5MB (메타데이터)
- **파일 크기**: ~165MB

## 🔄 워크플로우

### 서버 (GPU)

1. CLIP으로 이미지 임베딩 생성
2. FAISS 인덱스 구축
3. 파일 저장 (`.index`, `.json`, `.npy`)
4. 구글 드라이브에 업로드

### 로컬

1. 구글 드라이브에서 다운로드
2. `FAISSManager`로 로드
3. 검색 수행

## 📝 파일 포맷

### metadata.json

```json
[
  {
    "movie_id": 1,
    "title": "Toy Story",
    "genres": ["Animation", "Children", "Comedy"],
    "year": 1995,
    "poster_url": "https://..."
  },
  ...
]
```

### build_stats.json

```json
{
  "total_vectors": 80000,
  "vector_dim": 512,
  "distance_metric": "cosine",
  "build_date": "2025-11-14T10:30:00",
  "index_size_mb": 160.5,
  "metadata_size_mb": 5.2
}
```

## 🐛 트러블슈팅

### ImportError: FAISS is not installed

```bash
pip install faiss-cpu
```

### FileNotFoundError: Index file not found

인덱스를 먼저 생성해야 합니다:

```bash
python -m vector_store.build_index --output_dir ./vector_store/indices
```

### 검색 결과가 없음

필터 조건이 너무 엄격한지 확인하세요. `search_multiplier`를 늘리면 더 많은 후보를 검색합니다.

## 🔗 관련 문서

- [ADR 005: 벡터 저장소 선택](../docs/decisions/005-vector-database.md)
- [FAISS 공식 문서](https://github.com/facebookresearch/faiss/wiki)
- [CLIP 모델](https://github.com/openai/CLIP)

## 📦 버전 관리

인덱스 파일은 날짜 suffix로 버전 관리됩니다:

```
indices/
├── movie_posters.index          # 최신 버전 (심볼릭 링크처럼 사용)
├── movie_posters_20251114.index # 버전별 백업
├── metadata.json
└── metadata_20251114.json
```

구글 드라이브에도 버전별로 업로드하여 롤백이 가능합니다.

