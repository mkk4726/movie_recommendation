# LLM-based Search Query Dataset Generation

## 개요

BM25 등의 검색 엔진을 구현하면서, 관련 데이터셋이 없다보니 주관적인 평가 밖에 못하는 문제가 있었습니다.
이를 해결하기 위해 LLM을 활용해 synthetic query dataset을 생성하는 모듈입니다.

## 🎯 목표

1. **정답 데이터 생성**: 검색 시스템 학습/평가를 위한 `(query, movie)` 페어 데이터셋 구축
2. **다양한 쿼리 패턴**: 실제 사용자가 입력할 법한 자연어 검색 쿼리 생성
3. **Retrieval 모델 개선**: 생성된 데이터로 semantic search, BM25, dense retrieval 등의 성능 향상

## 아이디어 정리

### 문제 상황
- MovieLens + TMDB 데이터는 영화 메타데이터(제목, 장르, 줄거리, 감독, 작가, 출연배우 등)만 제공
- 실제 사용자가 "어떤 쿼리로 이 영화를 검색하는가"에 대한 데이터 부재
- 검색 시스템의 정확도 평가 및 개선이 어려움

### 해결 방법
```text
[TMDB Metadata] → [LLM Prompt] → [Synthetic Queries] → [Dataset]
(title, overview, genre, actors, keywords)
```

영화 메타데이터 (가능하다면 평가 데이터를 함께)를 LLM에 입력하고, 해당 영화를 찾기 위해 사용자가 입력할 수 있는 자연어 쿼리를 생성

## 🔄 워크플로

### 1. 데이터 수집 (data_scraping module 참고)
```python
# TMDB + MovieLens 메타데이터 로드
- movie_id
- title (한글/영문)
- overview (줄거리)
- genres
- actors/directors
- keywords
- release_date
```

### 2. LLM 프롬프트 설계

#### 예시 프롬프트
```text
You are a movie fan. Given the following movie metadata, generate 5-10 natural-language 
search queries that a Korean user might type to find this movie.

Title: Inception (인셉션)
Genres: Sci-Fi, Thriller, Action
Overview: A thief who steals corporate secrets through dream-sharing technology is given 
the inverse task of planting an idea into the mind of a C.E.O.
Director: Christopher Nolan
Actors: Leonardo DiCaprio, Joseph Gordon-Levitt, Ellen Page
Keywords: dream, subconscious, heist, mind manipulation

Generate diverse query types:
1. Plot-based: "꿈속에서 임무를 수행하는 영화"
2. Actor-based: "디카프리오가 나오는 SF 스릴러"
3. Mood/Theme-based: "복잡한 플롯의 마인드벤딩 영화"
4. Director-based: "놀란 감독의 꿈 관련 영화"
5. Keyword-based: "시간이 느리게 흐르는 꿈 이야기"

Output as JSON:
[
  {"query": "...", "query_type": "plot", "language": "ko"},
  ...
]
```

### 3. 쿼리 생성
- **LLM 모델**: GPT-4, Claude, 또는 오픈소스 LLM (Llama, Mistral 등)
- **Temperature**: 0.8~1.0 (다양성 확보)
- **영화당 생성 수**: 5~10개 쿼리
- **언어**: 한국어/영어 혼합

### 4. 데이터셋 구성

#### 최종 데이터 포맷
| movie_id | title      | query                          | query_type | language | source_llm    | relevance_score | created_at   |
|----------|------------|-------------------------------|------------|----------|---------------|-----------------|--------------|
| 27205    | Inception  | 꿈속에서 임무를 수행하는 영화        | plot       | ko       | gpt-4-turbo   | 1.0             | 2025-11-11   |
| 27205    | Inception  | 디카프리오 SF 영화                | actor      | ko       | gpt-4-turbo   | 0.9             | 2025-11-11   |
| 27205    | Inception  | 놀란 감독의 복잡한 플롯 영화         | director   | ko       | gpt-4-turbo   | 0.95            | 2025-11-11   |

#### 필드 설명
- `movie_id`: MovieLens/TMDB 영화 ID
- `title`: 영화 제목
- `query`: 생성된 검색 쿼리
- `query_type`: 쿼리 유형 (plot, actor, director, genre, mood, keyword 등)
- `language`: 쿼리 언어 (ko, en)
- `source_llm`: 사용된 LLM 모델명
- `relevance_score`: 관련도 점수 (0.0~1.0)
- `created_at`: 생성 시각

## 🎨 쿼리 유형 (Query Types)

1. **plot**: 줄거리 기반
   - "타임루프로 같은 날을 반복하는 영화"
   - "외계인과 소통하는 언어학자 이야기"

2. **overview**: 개요 기반
   - "가족의 의미를 되새기는 따뜻한 이야기"
   - "인간의 욕망과 파멸을 그린 느와르"

3. **actor**: 배우 기반
   - "송강호가 나오는 스릴러"
   - "디카프리오와 와타나베 켄이 같이 나온 영화"

4. **director**: 감독 기반
   - "봉준호 감독의 괴물 영화"
   - "놀란 감독 시간 관련 영화"

5. **genre**: 장르 기반
   - "SF 액션 스릴러"
   - "감성적인 로맨스 드라마"

6. **hybrid**: 복합 쿼리
   - "2000년대 한국 범죄 스릴러 영화"
   - "우주 배경 감동적인 SF 영화"

---

## 📊 활용 방안

(query, movie_id) 데이터셋이 있으면 검색 기능을 평가하고 고도화할 수 있습니다.

### 1. Retrieval 시스템 평가
```python
# 생성된 데이터셋으로 검색 성능 평가
- Precision@K
- Recall@K
- MRR (Mean Reciprocal Rank)
- NDCG (Normalized Discounted Cumulative Gain)
```

### 2. Embedding 모델 Fine-tuning
```python
# Contrastive learning with (query, movie_overview) pairs
- Sentence-BERT
- E5, GTE, BGE-M3
- ColBERT
```

### 3. Reranker 학습
```python
# Cross-encoder 학습
positive: (query, target_movie)
negatives: (query, similar_but_wrong_movies)
```

### 4. BM25 파라미터 튜닝
```python
# 생성된 쿼리로 k1, b 파라미터 최적화
```

---


## 🚀 확장 방향

### Phase 2: 품질 개선
- [ ] Human verification (샘플 1~2% 검증)
- [ ] Query diversity 분석
- [ ] Hard negative mining
- [ ] Relevance score 보정

### Phase 3: 고도화
- [ ] **LLM Self-play**: LLM이 생성한 쿼리로 retrieval → LLM이 결과 평가
- [ ] **Active learning**: 검색 성능이 낮은 영화에 대해 추가 쿼리 생성
- [ ] **User feedback loop**: 실제 사용 로그(클릭률, dwell time)로 relevance score 업데이트
- [ ] **Multilingual expansion**: 영어, 일본어 등 다국어 쿼리 생성

### Phase 4: 프로덕션 통합
- [ ] Retrieval 모델 재학습
- [ ] A/B 테스트로 검색 품질 개선 검증
- [ ] 지속적 데이터셋 업데이트 파이프라인

---

## 🧠 품질 향상 팁

### 1. LLM 설정 최적화
- **Temperature**: 0.8~1.0 (다양성 ↑)
- **Top-p**: 0.9~0.95
- **Frequency penalty**: 0.3~0.5 (반복 방지)

### 2. 프롬프트 엔지니어링
- Few-shot examples 제공
- 쿼리 유형별 가이드라인 명시
- 한국어 자연스러움 강조

### 3. 데이터 다양성 확보
- 장르별 균형 유지
- 인기도별 샘플링 (인기작 + 비인기작)
- 시대별 다양성 (고전 영화 + 최신 영화)

### 4. Negative Sampling 전략
```python
# Hard negatives 생성
- 같은 장르, 다른 줄거리
- 같은 배우, 다른 영화
- 비슷한 키워드, 다른 맥락
```

### 5. 검증 프로세스
- 샘플링된 쿼리 수동 검토
- Retrieval 시스템으로 실제 테스트
- Inter-annotator agreement 측정 (여러 LLM 결과 비교)

---

## 📚 참고 자료

### 관련 연구
- InPars (Bonifacio et al., 2022): LLM을 이용한 IR 데이터셋 생성
- Promptagator (Dai et al., 2022): Query generation for dense retrieval
- GPL (Wang et al., 2021): Generative Pseudo Labeling for unsupervised dense retrieval

### 유사 프로젝트
- MS MARCO: Large-scale information retrieval dataset
- Natural Questions: Question-answering dataset
- BEIR: Heterogeneous IR benchmark

## 🤝 기여 가이드

1. 새로운 쿼리 유형 추가
2. 프롬프트 템플릿 개선
3. 품질 평가 메트릭 제안
4. 다국어 지원 확장

