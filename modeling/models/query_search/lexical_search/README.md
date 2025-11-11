# Lexical Search Module

어휘 기반 검색(Lexical Search) 모듈입니다. 현재 BM25 알고리즘을 지원합니다.

## 구조

```
lexical_search/
├── __init__.py           # 모듈 진입점
├── bm25/                 # BM25 검색 모듈
│   ├── __init__.py       # BM25 모듈 진입점
│   ├── config.py         # 설정 관리
│   ├── tokenizer.py      # 토크나이저
│   ├── core.py           # BM25 핵심 알고리즘
│   ├── movie_search.py   # 영화 검색 특화 클래스
│   ├── models.py         # 데이터 모델
│   └── example.py        # 사용 예시
└── README.md             # 이 파일
```

## 사용법

### 기본 사용

```python
from modeling.models.query_search.lexical_search import MovieBM25, BM25Config
import pandas as pd

# 1. 설정 로드 (YAML 파일에서)
config = BM25Config.from_yaml()

# 2. MovieBM25 초기화
movie_bm25 = MovieBM25(config=config)

# 3. 영화 데이터로 색인 생성
movies_df = pd.read_csv("movies.csv")
movie_bm25.fit(movies_df)

# 4. 검색
results = movie_bm25.search("toy story", top_k=10)

# 5. 결과 출력
for result in results:
    print(f"{result.title} - Score: {result.score:.2f}")
```

### 색인 저장 및 로드

```python
# 색인 저장
movie_bm25.save("./cache/bm25_index")

# 색인 로드
loaded_bm25 = MovieBM25.load("./cache/bm25_index")
```

### 커스텀 설정

```python
# 코드에서 직접 설정 생성
config = BM25Config(
    k1=1.5,
    b=0.75,
    top_k=20,
    field_weights={
        'title': 3.0,
        'genres': 2.0,
        'tags': 1.0
    }
)

movie_bm25 = MovieBM25(config=config)
```

## 모듈 설명

### config.py
- `BM25Config`: BM25 알고리즘 및 검색 설정을 관리하는 데이터 클래스
- YAML 파일에서 설정을 로드하거나 코드에서 직접 생성 가능

### tokenizer.py
- `BM25Tokenizer`: 텍스트를 토큰으로 분리하는 토크나이저
- 한글과 영어를 모두 지원
- 특수 문자 제거, 길이 필터링 등의 기능 제공

### core.py
- `BM25`: BM25 알고리즘의 핵심 구현
- 색인 생성, 검색, 저장/로드 기능 제공
- 단일 필드에 대한 BM25 검색 수행

### movie_search.py
- `MovieBM25`: 영화 검색에 특화된 BM25 래퍼 클래스
- 여러 필드(제목, 장르, 태그 등)에 대해 가중치를 적용한 통합 검색
- 필드별 스코어를 결합하여 최종 랭킹 생성

### models.py
- `BM25SearchResult`: 검색 결과를 담는 데이터 클래스
- 영화 ID, 스코어, 제목, 장르, 필드별 매칭 정보 포함

## 설정 파일 (config.yaml)

```yaml
bm25:
  # BM25 파라미터
  k1: 1.5              # 용어 빈도 포화 파라미터 (1.2~2.0 권장)
  b: 0.75              # 문서 길이 정규화 파라미터 (0~1)
  epsilon: 0.25        # IDF 하한값
  
  # 검색 설정
  top_k: 20            # 반환할 상위 결과 개수
  min_score: 0.0       # 최소 스코어 임계값
  
  # 토크나이저 설정
  use_korean: true     # 한글 지원
  min_token_length: 1  # 최소 토큰 길이
  max_token_length: 50 # 최대 토큰 길이
  
  # 필드 가중치
  field_weights:
    title: 3.0         # 제목
    genres: 2.0        # 장르
    tags: 1.0          # 태그
    overview: 1.5      # 줄거리
```

## 예시 실행

```bash
cd modeling/models/query_search/lexical_search/bm25
python -m example
```

## BM25 알고리즘 설명

BM25 (Best Matching 25)는 정보 검색에서 가장 널리 사용되는 랭킹 함수입니다.

### 주요 특징
1. **용어 빈도 포화**: 같은 단어가 여러 번 나와도 스코어가 무한정 증가하지 않음
2. **문서 길이 정규화**: 긴 문서가 유리하지 않도록 조정
3. **IDF (Inverse Document Frequency)**: 희귀한 단어에 더 높은 가중치

### 공식

```
score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D| / avgdl))
```

여기서:
- `D`: 문서
- `Q`: 쿼리
- `qi`: 쿼리의 i번째 용어
- `f(qi,D)`: 문서 D에서 용어 qi의 빈도
- `|D|`: 문서 D의 길이
- `avgdl`: 평균 문서 길이
- `k1`: 용어 빈도 포화 파라미터 (일반적으로 1.2~2.0)
- `b`: 문서 길이 정규화 파라미터 (일반적으로 0.75)

## 향후 계획

- TF-IDF 검색 추가
- BM25+ 알고리즘 구현
- 형태소 분석기 통합 (한글 검색 개선)
- 동의어 확장 기능

