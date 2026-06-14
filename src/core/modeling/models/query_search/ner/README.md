# NER (Named Entity Recognition) Module

영화 추천 쿼리에서 엔티티(배우, 감독, 장르 등)를 추출하는 모듈입니다.

## 모듈 구성

### 1. QwenBasedNER (Qwen LLM 기반)
- **용도**: 전체 엔티티 추출 (배우, 감독, 장르, 연도, 영화 제목, 지역, 키워드 등)
- **모델**: Qwen/Qwen2.5-3B-Instruct
- **특징**: 
  - 정확한 엔티티 분류
  - JSON 형식으로 구조화된 출력
  - 장르 정규화 (예: "로맨틱한" → "로맨스")
- **단점**: 추론 시간이 다소 소요됨 (~15초)

### 2. GLiNERPersonExtractor (GLiNER 기반)
- **용도**: 사람 이름만 추출 (배우, 감독 등)
- **모델**: taeminlee/gliner_ko
- **특징**:
  - 빠른 추론 속도
  - 경량화된 모델
  - PERSON 엔티티만 추출
- **단점**: 사람 이름 외의 엔티티는 추출 불가

## 설치

```bash
# Qwen 기반 NER
pip install torch transformers accelerate

# GLiNER 기반 Person Extractor
pip install gliner
```

## 사용법

### QwenBasedNER - 전체 엔티티 추출

```python
from modeling.models.query_search.ner import QwenBasedNER

# 초기화 (config.yaml에서 설정 자동 로드)
ner = QwenBasedNER()

# 쿼리 분석
query = "김민규가 나오는 진지한 분위기의 로맨스 액션 영화 추천해줘"
result = ner.run(query, verbose=True)

# 결과 확인
print(result.actors)          # ['김민규']
print(result.genres)          # ['로맨스', '액션']
print(result.story_keywords)  # ['진지한']
print(result.other_keywords)  # ['추천']

# 딕셔너리로 변환
print(result.to_dict())
```

### GLiNERPersonExtractor - 사람 이름만 추출

```python
from modeling.models.query_search.ner import GLiNERPersonExtractor

# 초기화
extractor = GLiNERPersonExtractor()

# 방법 1: 상세 결과
query = "박찬욱 감독과 송강호가 출연한 영화"
result = extractor.extract_persons(query, threshold=0.3, verbose=True)
print(result.persons)  # ['박찬욱', '송강호']

# 방법 2: 간단 사용 (리스트만 반환)
persons = extractor(query, threshold=0.3)
print(persons)  # ['박찬욱', '송강호']
```

## 설정 파일 (config.yaml)

### Qwen NER 설정

```yaml
ner:
  model_name: "Qwen/Qwen2.5-3B-Instruct"
  max_new_tokens: 128
  temperature: 0.0
  do_sample: false
  mps_single_device: true
  
  system_prompt: |
    You are a specialized information extraction system for movie queries...
    (전체 프롬프트는 config.yaml 참조)
```

## 출력 형식

### NERResult (QwenBasedNER)

```python
@dataclass
class NERResult:
    actors: List[str]          # 배우 이름
    genres: List[str]          # 장르
    years: List[int]           # 연도
    directors: List[str]       # 감독 이름
    movie_titles: List[str]    # 영화 제목
    regions: List[str]         # 지역/국가
    story_keywords: List[str]  # 스토리 키워드
    other_keywords: List[str]  # 기타 키워드
```

### PersonExtractionResult (GLiNERPersonExtractor)

```python
@dataclass
class PersonExtractionResult:
    persons: List[str]         # 추출된 사람 이름
    raw_entities: List[Dict]   # 원본 엔티티 정보 (신뢰도 포함)
```

## 테스트

### QwenBasedNER 테스트

```bash
cd modeling/models/query_search/ner
python qwen_based.py
```

### GLiNERPersonExtractor 테스트

```bash
cd modeling/models/query_search/ner
python gliner_based.py
```

## 성능 비교

| 모델 | 추론 속도 | 추출 범위 | 정확도 | 메모리 |
|------|----------|----------|--------|--------|
| QwenBasedNER | ~15초 | 전체 엔티티 | 높음 | 높음 |
| GLiNERPersonExtractor | ~1초 | 사람 이름만 | 중상 | 낮음 |

## 사용 권장 사항

- **전체 쿼리 분석이 필요한 경우**: `QwenBasedNER` 사용
  - 장르, 연도, 키워드 등 다양한 필터링 조건 추출
  - 복잡한 쿼리 파싱

- **사람 이름만 빠르게 추출하고 싶은 경우**: `GLiNERPersonExtractor` 사용
  - 배우/감독 검색 기능
  - 실시간 자동완성
  - 빠른 응답이 필요한 경우

## 통합 사용 예시

```python
from modeling.models.query_search.ner import QwenBasedNER, GLiNERPersonExtractor

# 전체 분석
qwen_ner = QwenBasedNER()
result = qwen_ner.run("크리스토퍼 놀란 감독의 2020년 이후 SF 영화 추천해줘")

print(f"감독: {result.directors}")      # ['크리스토퍼 놀란']
print(f"장르: {result.genres}")         # ['SF']
print(f"연도: {result.years}")          # [2020]

# 빠른 사람 이름 추출
person_extractor = GLiNERPersonExtractor()
persons = person_extractor("이병헌과 하정우가 출연한 영화")
print(f"출연자: {persons}")  # ['이병헌', '하정우']
```

## 문제 해결

### ImportError: gliner 모듈을 찾을 수 없음
```bash
pip install gliner
```

### ImportError: transformers 모듈을 찾을 수 없음
```bash
pip install transformers torch accelerate
```

### CUDA Out of Memory
- `config.yaml`에서 `mps_single_device: false` 설정
- 더 작은 모델 사용: `Qwen/Qwen2.5-1.5B-Instruct`

## 라이센스

이 모듈은 프로젝트 라이센스를 따릅니다.

