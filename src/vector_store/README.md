# Vector Store

FAISS 기반 벡터 저장소 및 유사도 검색 모듈

## 📁 구조

```
vector_store/
├── __init__.py              # 모듈 초기화
├── config.yaml              # 설정 파일
├── utils/
│   ├── __init__.py          # 설정 유틸 export
│   └── config.py            # YAML 로더
├── faiss_manager.py         # FAISS 인덱스 관리
├── build_index.py           # 인덱스 빌더 클래스
├── create_vector_store.py   # Vector Store 생성 실행 스크립트 ⭐
├── test_search.py           # 검색 테스트 스크립트 🧪
├── indices/                 # 인덱스 파일 저장 (gitignore)
│   ├── movie_posters.index
│   ├── movie_ids.json
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

### 2. Vector Store 생성 (한 번만 실행)

**방법 1: 커맨드라인 실행 (권장)**

```bash
# 기본 설정으로 실행
python -m vector_store.create_vector_store

# 백그라운드 실행 (nohup)
nohup python -m vector_store.create_vector_store > vector_store.log 2>&1 &

# 로그 확인
tail -f vector_store.log
```

설정을 변경하려면 `vector_store/config.yaml` 파일을 수정하세요:
- `index.base_dir`: 출력 디렉토리
- `build.timeout`: HTTP 요청 타임아웃
- `build.download_batch_size`: 동시 다운로드할 이미지 수 (기본: 100)
- `build.encoding_batch_size`: GPU 배치 인코딩 크기 (기본: 32)
- `build.max_workers`: 다운로드 스레드 수 (기본: 20)
- `build.max_retries`: 다운로드 재시도 횟수 (기본: 3)
- `build.save_embeddings`: 임베딩 원본 저장 여부

**방법 2: Python 코드로 실행**

```python
from pathlib import Path
from vector_store.create_vector_store import VectorStoreCreator

# Creator 초기화 (config.yaml 사용)
creator = VectorStoreCreator()

# Vector Store 생성
creator.create()
```

이 스크립트는 자동으로:
- 영화 데이터를 로드하고
- TMDB에서 포스터 이미지를 다운로드하고
- CLIP 모델로 임베딩을 생성하고
- FAISS 인덱스를 빌드하여 저장합니다

### 3. 검색 테스트

**방법 1: 테스트 스크립트 실행 (권장)**

```bash
# 기본 테스트 실행 (랜덤 벡터, 배치 검색, 텍스트 검색)
python -m vector_store.test_search
```

이 스크립트는 자동으로:
- 인덱스를 로드하고
- 랜덤 벡터로 검색 성능을 측정하고
- 배치 검색 처리량을 테스트하고
- CLIP 모델로 텍스트 검색을 수행합니다

**방법 2: Python 코드로 직접 검색**

```python
from vector_store import FAISSManager

# 매니저 초기화 (기본 설정 사용)
manager = FAISSManager()
manager.load()

# 유사도 검색
query_vector = clip_model.encode_image(query_image)
results = manager.search(query_vector, k=10)

for result in results:
    print(f"index={result['index']} (score: {result['score']:.3f})")
```

## 📖 사용 예시

### 기본 검색

```python
# 벡터로 검색
results = manager.search(query_vector, k=10)
```

필터링, 영화 ID 기반 검색, 메타데이터 조회 기능은 제거되었습니다. 필요한 경우 외부에서 별도 매핑을 관리하세요.

### 검색 테스트 스크립트 사용법

`test_search.py`는 다양한 검색 테스트를 제공합니다:

```python
from vector_store.test_search import VectorSearchTester

# 테스터 초기화
tester = VectorSearchTester()

# 1. 인덱스 통계 정보
tester.test_statistics()

# 2. 랜덤 벡터 검색 (성능 측정)
tester.test_random_search(k=10, num_queries=5)

# 3. 배치 검색 (처리량 측정)
tester.test_batch_search(batch_size=100, k=10)

# 4. 영화 데이터 로드 (포스터 시각화용)
tester.load_movie_data()

# 5. CLIP 인코더 로드
tester.load_encoder(model_key="jina-clip")

# 6. 텍스트 검색 (포스터 이미지 시각화 포함)
tester.test_text_search("action movie with explosions", k=10, visualize=True)

# 7. 이미지 검색 (쿼리 이미지와 결과 함께 시각화)
tester.test_image_search("path/to/image.jpg", k=10, visualize=True)

# 8. 시각화만 따로 실행
results = tester.manager.search(query_vector, k=10)
tester.visualize_results(results, query_image_path="path/to/query.jpg")
```

**시각화 기능:**
- `visualize=True` 옵션으로 검색 결과를 포스터 이미지 그리드로 표시
- matplotlib을 사용하여 영화 제목과 유사도 점수와 함께 표시
- 이미지 검색 시 쿼리 이미지도 함께 표시
- 필요한 패키지: `matplotlib`, `requests`, `PIL`

**테스트 결과 예시:**
```
랜덤 벡터 검색 테스트 (k=10, queries=5)
쿼리 1:
  검색 시간: 0.85ms
  결과 수: 10개
    1. index= 12345, score=0.8234
    2. index= 67890, score=0.8102
    3. index= 23456, score=0.7998

평균 검색 시간: 0.87ms
초당 쿼리 수: 1149.4 QPS
```

## 🔧 설정

### config.yaml

```yaml
# 인덱스 파일 경로
index:
  base_dir: "vector_store/indices"
  index_file: "movie_posters.index"
  embeddings_file: "embeddings.npy"

# 벡터 설정
vector:
  dim: 768  # Jina CLIP 벡터 차원
  distance_metric: "cosine"  # cosine, l2, ip

# 검색 설정
search:
  default_k: 10  # 기본 검색 결과 수
  search_multiplier: 10  # 필터링 시 추가 검색 배수

# 빌드 설정
build:
  save_embeddings: true      # 임베딩 원본 저장 여부
  save_versioned: true       # 버전별 파일 저장 여부
  timeout: 10                # HTTP 요청 타임아웃 (초)
  download_batch_size: 100   # 동시 다운로드할 이미지 수
  encoding_batch_size: 32    # GPU 배치 인코딩 크기
  max_workers: 20            # 다운로드 스레드 수
  max_retries: 3             # 다운로드 재시도 횟수
```

### 설정 로드

```python
from vector_store import load_config

# 기본 설정 로드
config = load_config()

# 커스텀 설정 파일 사용
config = load_config("path/to/custom_config.yaml")

# 특정 경로 가져오기
from vector_store import get_index_path

index_path = get_index_path(config)
```

## 📊 성능

### 검색 성능
- **검색 속도**: ~0.5-1ms (8만 벡터 기준)
- **메모리 사용**: ~160MB (인덱스)
- **파일 크기**: ~160MB + movie_ids JSON 수 KB

### 빌드 성능 최적화

벡터 스토어 생성 시 다음 최적화 기법을 사용합니다:

1. **멀티스레딩 다운로드**: 최대 20개 스레드로 동시 이미지 다운로드
2. **배치 인코딩**: GPU에서 32개 이미지를 한 번에 인코딩
3. **재시도 로직**: 네트워크 오류 시 최대 3회 재시도
4. **메모리 효율**: 100개씩 배치 단위로 처리하여 메모리 사용 최소화

**예상 처리 속도**: 
- GPU 사용 시: ~500-1000 영화/분 (순차 처리 대비 **5-10배** 향상)
- CPU 사용 시: ~100-200 영화/분

**처리 시간 예측**:
| 영화 수 | 이전 | 개선 후 | 절감 시간 |
|--------|------|---------|----------|
| 10,000 | ~100분 | ~10-20분 | ~80-90분 |
| 50,000 | ~500분 | ~50-100분 | ~400-450분 |
| 80,000 | ~800분 | ~80-160분 | ~640-720분 |

### 환경별 권장 설정

#### 고성능 GPU 서버 (A100, V100)
```yaml
download_batch_size: 200
encoding_batch_size: 64
max_workers: 30
```

#### 중급 GPU (RTX 3090, 4090)
```yaml
download_batch_size: 100
encoding_batch_size: 32
max_workers: 20
```

#### 저사양 GPU (GTX 1080, RTX 2060)
```yaml
download_batch_size: 50
encoding_batch_size: 16
max_workers: 10
```

#### CPU 전용
```yaml
download_batch_size: 50
encoding_batch_size: 8
max_workers: 10
```

### 성능 튜닝 가이드

1. **GPU 활용도 확인**
   ```bash
   watch -n 1 nvidia-smi
   ```
   - GPU 사용률이 낮으면 `encoding_batch_size` 증가

2. **네트워크 대역폭 확인**
   ```bash
   iftop
   ```
   - 대역폭 여유 있으면 `max_workers` 증가

3. **메모리 사용량 확인**
   ```bash
   htop
   ```
   - 메모리 여유 있으면 `download_batch_size` 증가

### 트러블슈팅

**메모리 부족**
```yaml
download_batch_size: 50
encoding_batch_size: 16
```

**GPU 메모리 부족**
```yaml
encoding_batch_size: 8
```

**네트워크 타임아웃 빈번**
```yaml
timeout: 30
max_retries: 5
```

**다운로드 속도 느림**
```yaml
max_workers: 50
```

## 🔄 워크플로우

### 서버 (GPU)

1. CLIP으로 이미지 임베딩 생성
2. FAISS 인덱스 구축
3. 파일 저장 (`.index`, `movie_ids.json`, `.npy`)
4. 구글 드라이브에 업로드

### 로컬

1. 구글 드라이브에서 다운로드
2. `FAISSManager`로 로드
3. 검색 수행

### build_stats.json

```json
{
  "total_vectors": 80000,
  "vector_dim": 512,
  "distance_metric": "cosine",
  "build_date": "2025-11-14T10:30:00",
  "index_size_mb": 160.5
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
python -m vector_store.create_vector_store
```

### 검색 결과가 없음

쿼리 벡터가 정규화되었는지 확인하고, `search_multiplier` 설정으로 검색 후보 수를 조정하세요.

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
├── movie_ids.json
├── movie_ids_20251114.json
├── embeddings.npy
└── embeddings_20251114.npy
```

구글 드라이브에도 버전별로 업로드하여 롤백이 가능합니다.

