# Query Search Pipeline

자연어 검색 파이프라인 - 사용자의 자연어 쿼리로 영화를 검색합니다.

## 개요

`QuerySearchPipeline`은 사용자의 자연어 쿼리를 받아서 영화 검색 결과를 반환하는 파이프라인입니다.
현재는 BM25 기반 lexical search를 사용하여 제목, 장르, 줄거리 등 여러 필드를 통합 검색합니다.

## 주요 기능

- ✅ 자연어 쿼리 기반 영화 검색
- ✅ 다중 필드 검색 (제목, 장르, 줄거리 등)
- ✅ 필드별 가중치 적용
- ✅ 검색 인덱스 저장/로드 (빠른 재시작)
- ✅ **Pydantic 모델 기반 타입 안전한 결과 반환** (API 응답용)
- ✅ 딕셔너리 형태 결과 반환 지원

## 설치 및 설정

### 1. 설정 파일 (config.yaml)

`modeling/models/config.yaml`에서 BM25 검색 설정을 관리합니다:

```yaml
bm25:
  # BM25 알고리즘 하이퍼파라미터
  k1: 1.5               # 용어 빈도 포화 파라미터
  b: 0.75               # 문서 길이 정규화 파라미터
  epsilon: 0.25         # IDF 하한값
  
  # 검색 설정
  top_k: 20             # 반환할 상위 결과 개수
  min_score: 0.0        # 최소 스코어 임계값
  
  # 필드 가중치 (영화 검색에 최적화)
  field_weights:
    title: 3.0          # 제목에 가장 높은 가중치
    genres: 2.0         # 장르에 중간 가중치
    tags: 1.0           # 태그에 기본 가중치
    overview: 1.5       # 줄거리/개요에 중간 가중치
```

## 사용법

### 기본 사용법

```python
from modeling.models.query_search import QuerySearchPipeline
from data_scraping.common import load_movie_data

# 1. 영화 데이터 로드
movie_data = load_movie_data()

# 2. 파이프라인 초기화 (config.yaml에서 설정 로드)
pipeline = QuerySearchPipeline()

# 3. 영화 데이터로 검색 인덱스 생성
pipeline.fit(movie_data)

# 4. 검색
results = pipeline.search("toy story", top_k=10)

# 5. 결과 출력
for result in results:
    print(f"{result.title} - Score: {result.score:.2f}")
    print(f"Genres: {result.genres}")
    print(f"Matched Fields: {result.matched_fields}")
    print()
```

### 검색 예제

#### 1. 영화 제목으로 검색

```python
results = pipeline.search("toy story", top_k=5)
# Toy Story (1995), Toy Story 2, Toy Story 3 등 반환
```

#### 2. 장르로 검색

```python
results = pipeline.search("action adventure", top_k=10)
# Action, Adventure 장르 영화들 반환
```

#### 3. 줄거리로 검색

```python
results = pipeline.search("superhero saves the world", top_k=10)
# 줄거리에 해당 키워드가 포함된 영화들 반환
```

#### 4. 복합 검색

```python
results = pipeline.search("romantic comedy paris", top_k=10)
# 제목, 장르, 줄거리를 통합하여 검색
```

### Pydantic 모델로 결과 받기 (권장, API 응답용)

```python
from app.api.models import QuerySearchResponse

# Pydantic 모델로 반환 (타입 안전)
response: QuerySearchResponse = pipeline.search_to_response("toy story", top_k=5)

# 자동 완성 및 타입 체크 지원
print(f"Query: {response.query}")
print(f"Total: {response.total_results}")

for movie in response.results:
    print(f"{movie.title} (score: {movie.score})")
    print(f"  Genres: {movie.genres}")
    print(f"  Matched: {movie.matched_fields}")

# JSON으로 변환
json_data = response.model_dump()
json_str = response.model_dump_json()
```

### 딕셔너리 형태로 결과 받기

```python
result_dict = pipeline.search_to_dict("toy story", top_k=5)

# 결과 구조:
# {
#     "query": "toy story",
#     "total_results": 5,
#     "results": [
#         {
#             "movie_id": "1",
#             "score": 44.09,
#             "title": "Toy Story (1995)",
#             "genres": "Adventure Animation Children Comedy Fantasy",
#             "overview": "...",
#             "matched_fields": {"title": 44.09},
#             "year": 1995
#         },
#         ...
#     ]
# }
```

### 검색 인덱스 저장 및 로드

검색 인덱스를 저장하면 다음 실행 시 빠르게 시작할 수 있습니다:

```python
# 인덱스 저장
pipeline.save("./search_index")

# 저장된 인덱스 로드 (fit() 불필요)
loaded_pipeline = QuerySearchPipeline.load("./search_index")

# 바로 검색 가능
results = loaded_pipeline.search("matrix", top_k=5)
```

### 편의 함수 사용

```python
from modeling.models.query_search import create_search_pipeline, search_movies

# 한 번에 파이프라인 생성 및 학습
pipeline = create_search_pipeline(movie_data)

# 검색 (기본: Pydantic 모델 반환)
response = search_movies(pipeline, "star wars", top_k=5)

# 반환 타입 지정
pydantic_response = search_movies(pipeline, "star wars", return_type="pydantic")  # 기본값
dict_result = search_movies(pipeline, "star wars", return_type="dict")
raw_results = search_movies(pipeline, "star wars", return_type="raw")  # BM25SearchResult 리스트
```

## API 통합 예제

FastAPI에서 사용하는 예제 (Pydantic 모델 사용):

```python
from fastapi import FastAPI, Query
from modeling.models.query_search import QuerySearchPipeline
from app.api.models import QuerySearchResponse

app = FastAPI()

# 앱 시작 시 파이프라인 로드
@app.on_event("startup")
async def startup_event():
    global search_pipeline
    search_pipeline = QuerySearchPipeline.load("./search_index")

# 검색 엔드포인트 (Pydantic 모델 자동 검증 및 문서화)
@app.get("/search", response_model=QuerySearchResponse)
async def search_movies(
    q: str = Query(..., description="검색 쿼리"),
    top_k: int = Query(20, ge=1, le=100, description="결과 개수")
):
    # Pydantic 모델 반환 (자동으로 JSON 변환 및 스키마 검증)
    return search_pipeline.search_to_response(q, top_k=top_k)
```

실제 프로젝트 통합 예제 (`app/api/routes/search.py`):

```python
from fastapi import APIRouter, HTTPException, Query
from app.api.models import QuerySearchResponse

router = APIRouter()

@router.get("/search/natural-language", response_model=QuerySearchResponse)
def natural_language_search(
    query: str = Query(..., min_length=1, description="자연어 검색 쿼리"),
    limit: int = Query(20, ge=1, le=100, description="반환할 최대 결과 수"),
    min_score: float = Query(0.0, ge=0.0, description="최소 검색 스코어 임계값"),
):
    """
    자연어 검색 API (BM25 기반)
    
    예시:
    - "toy story animation"
    - "action movies with robots"
    - "romantic comedy 2020"
    """
    pipeline = get_search_pipeline()  # 지연 로딩
    return pipeline.search_to_response(
        query=query,
        top_k=limit,
        min_score=min_score
    )
```

## 검색 결과 구조

### Pydantic 모델 (권장)

#### QuerySearchResponse

```python
class QuerySearchResponse(BaseModel):
    query: str                          # 검색 쿼리
    total_results: int                  # 전체 결과 개수
    results: List[SearchResultMovie]    # 검색 결과 리스트
```

#### SearchResultMovie

```python
class SearchResultMovie(BaseModel):
    movie_id: str                       # 영화 ID
    title: str                          # 영화 제목
    genres: str                         # 장르
    score: float                        # BM25 스코어 (높을수록 관련성 높음)
    overview: str                       # 영화 줄거리/개요
    matched_fields: Dict[str, float]    # 매칭된 필드별 스코어
    year: Optional[int]                 # 개봉 연도
```

### BM25SearchResult 객체 (Raw)

```python
class BM25SearchResult(BaseModel):
    movie_id: str           # 영화 ID
    score: float            # BM25 스코어 (높을수록 관련성 높음)
    title: str              # 영화 제목
    genres: str             # 장르
    overview: str           # 영화 줄거리/개요
    matched_fields: Dict    # 매칭된 필드별 스코어
    year: Optional[int]     # 개봉 연도
```

### matched_fields 설명

어떤 필드에서 매칭되었는지와 각 필드별 가중치 적용된 점수를 보여줍니다:

```python
# 예시 1: 제목에서만 매칭
matched_fields = {'title': 44.09}

# 예시 2: 제목과 장르에서 모두 매칭
matched_fields = {'title': 30.5, 'genres': 15.2}

# 예시 3: 줄거리에서만 매칭
matched_fields = {'overview': 12.8}
```

## 성능 최적화

### 1. 인덱스 사전 생성

프로덕션 환경에서는 인덱스를 미리 생성하고 저장해두세요:

```python
# 개발 환경에서 한 번만 실행
pipeline = QuerySearchPipeline()
pipeline.fit(movie_data)
pipeline.save("./production_index")

# 프로덕션 환경에서 빠르게 로드
pipeline = QuerySearchPipeline.load("./production_index")
```

### 2. 필드 가중치 조정

`config.yaml`에서 필드별 가중치를 조정하여 검색 품질을 개선할 수 있습니다:

```yaml
field_weights:
  title: 3.0      # 제목 매칭을 가장 중요하게
  genres: 2.0     # 장르 매칭을 중간 정도로
  overview: 1.5   # 줄거리 매칭을 낮게
```

### 3. top_k 및 min_score 조정

```python
# 더 많은 결과 반환
results = pipeline.search("action", top_k=50)

# 최소 점수 설정 (낮은 점수 필터링)
results = pipeline.search("action", top_k=20, min_score=5.0)
```

## 아키텍처

```
QuerySearchPipeline
    │
    ├── MovieBM25 (다중 필드 BM25 검색)
    │   ├── BM25 (title 필드)
    │   ├── BM25 (genres 필드)
    │   ├── BM25 (tags 필드)
    │   └── BM25 (overview 필드)
    │
    └── 검색 결과 통합 및 정렬
```

## 향후 개선 계획

- [ ] NER 기반 엔티티 추출 통합
- [ ] 의미 기반 검색 (Semantic Search) 추가
- [ ] 하이브리드 검색 (Lexical + Semantic)
- [ ] 사용자 피드백 기반 재순위화 (Re-ranking)
- [ ] 검색 쿼리 자동 완성
- [ ] 검색 로그 분석 및 개선

## 문제 해결

### 경고: 'tags' 필드가 데이터프레임에 없습니다

데이터에 없는 필드는 자동으로 건너뛰므로 무시해도 됩니다. 
필요하다면 `config.yaml`에서 해당 필드를 제거하세요.

### 검색 결과가 없음

- `min_score`를 낮추거나 0으로 설정해보세요
- 검색 쿼리를 더 간단하게 만들어보세요
- 데이터에 해당 영화가 실제로 있는지 확인하세요

### 메모리 부족

- 데이터를 샘플링하여 사용하세요
- `top_k` 값을 줄이세요
- 불필요한 필드를 `config.yaml`에서 제거하세요

## 라이센스

이 프로젝트는 MIT 라이센스를 따릅니다.

