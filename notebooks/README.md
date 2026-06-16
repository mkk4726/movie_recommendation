# Notebooks

실험 및 탐색용 Jupyter 노트북 모음. 검증된 로직은 `src/core/modeling/` 으로 이관됨.

```
notebooks/
├── modeling/          # 모델 실험 (CF, 검색, NER, 임베딩 등)
├── ab_test/           # 추천 품질 LLM 평가
└── dataset_generation/ # 합성 데이터 / 쿼리 생성
```

---

## modeling/

### Collaborative Filtering
| 노트북 | 내용 |
|---|---|
| `CF.ipynb` | ML-32M 기반 CF 전체 파이프라인. EDA(평점 분포·Long-tail·시계열·장르) → 전처리(cold-start 필터링, 시간 기반 train/test split) → 5종 모델(UserKNN, ItemKNN, SVD, SVD++, NMF) → RMSE/MAE + Precision@K/Recall@K/NDCG@K → SVD 하이퍼파라미터 그리드 서치 |

### 검색 (Query Search)
| 노트북 | 내용 |
|---|---|
| `BM25.ipynb` | title·overview·cast 필드에 BM25 적용한 렉시컬 검색. `src/core/modeling/models/query_search/lexical_search/bm25/` 로 이관됨 |
| `query_pipeline.ipynb` | BM25 + 메타데이터 매칭을 결합한 end-to-end 쿼리 검색 파이프라인 실험 |

### NER (Named Entity Recognition)
| 노트북 | 내용 |
|---|---|
| `NER.ipynb` | GLiNER-ko 기반 한국어 NER. 쿼리에서 배우·영화·감독 추출. `src/core/modeling/models/query_search/ner/` 로 이관됨 |
| `LLM-based-NER.ipynb` | Qwen-2.5 LLM 기반 NER 실험. 구조화된 정보(배우, 장르, 감독) 추출 |

### 임베딩 & 콘텐츠 기반
| 노트북 | 내용 |
|---|---|
| `clip.ipynb` | Jina·OpenCLIP·OpenAI CLIP 모델 비교. 영화 포스터 이미지 ↔ 텍스트 유사도 검색. `src/core/modeling/models/clip/` 으로 이관됨 |
| `movie-based.ipynb` | 배우·감독·작가·줄거리 메타데이터를 결합한 영화 임베딩으로 콘텐츠 기반 추천 |
| `filtering.ipynb` | 장르·출연진·감독 메타데이터 기반 콘텐츠 필터링 및 랭킹 |

### 기타
| 노트북 | 내용 |
|---|---|
| `clustering.ipynb` | KMeans·DBSCAN·GMM·MiniBatchKMeans로 유저 126K+ 세그멘테이션 (평점 통계 + 장르 선호도 피처 사용) |
| `translate.ipynb` | MarianMT 기반 다국어 번역 및 언어 감지. `src/core/modeling/models/language/` 으로 이관됨 |

---

## ab_test/

| 노트북 | 내용 |
|---|---|
| `example.ipynb` | Claude LLM 평가자로 두 추천 시스템 비교 (sci-fi·thriller 유저 컨텍스트 기준 선호도 스코어링) |
| `search.ipynb` | 다양한 유저 페르소나(스릴러 매니아, SF 팬 등)를 기준으로 BM25 검색 결과를 LLM 평가자로 품질 평가 |

---

## dataset_generation/

| 노트북 | 내용 |
|---|---|
| `generate_query.ipynb` | Qwen-2.5-1.5B으로 합성 영화 검색 쿼리 생성 (배우·장르·무드·줄거리·복합 카테고리) |
| `load_model_generate_test.ipynb` | 학습된 SVD 모델 로드 후 특정 유저 Top-10 추천 생성 테스트 |
