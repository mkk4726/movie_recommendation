# 영화 추천 시스템 모델링

이 폴더는 영화 추천 시스템을 위한 머신러닝 모델링 코드를 포함합니다.

## 📁 파일 구조

```
modeling/
├── movie_recommendation_modeling.ipynb  # 메인 모델링 노트북
├── movie_recommendation_model.pkl       # 저장된 모델 파일 (실행 후 생성)
└── README.md                           # 이 파일
```

## 🎯 주요 기능

### 1. 데이터 로딩 및 전처리
- `../data_scraping/data/` 폴더에서 수집된 데이터 로드
- 영화 정보, 사용자 평점, 영화 리뷰 데이터 전처리
- 결측치 처리 및 데이터 정제

### 2. 탐색적 데이터 분석 (EDA)
- 평점 분포 시각화
- 사용자/영화별 평점 수 분석
- 장르별 영화 분포 분석

### 3. 협업 필터링 (Collaborative Filtering)
- **Matrix Factorization (SVD)** 기반 추천 시스템
- User-Item 평점 행렬 생성
- Train/Test 데이터 분할
- RMSE, MAE를 이용한 모델 평가

### 4. 컨텐츠 기반 필터링 (Content-Based Filtering)
- **TF-IDF** 벡터화를 통한 영화 특성 추출
- **Cosine Similarity**를 이용한 영화 간 유사도 계산
- 장르 및 줄거리 기반 유사 영화 추천

### 5. 하이브리드 추천 시스템
- 협업 필터링 + 컨텐츠 기반 필터링 결합
- 가중치 조정을 통한 최적 추천
- 사용자 개인화 추천 구현

## 🚀 사용 방법

### 1. 환경 설정

```bash
# 프로젝트 루트로 이동
cd /Users/visuworks/Desktop/movie_recommendation

# 필요한 패키지 설치 (requirements.txt 또는 pyproject.toml 사용)
pip install pandas numpy matplotlib seaborn scikit-learn scipy
```

### 2. Jupyter Notebook 실행

```bash
# modeling 폴더로 이동
cd modeling

# Jupyter Notebook 실행
jupyter notebook movie_recommendation_modeling.ipynb
```

### 3. 셀 실행
- 노트북의 셀을 순서대로 실행
- 각 섹션별로 결과 확인
- 마지막에 모델이 `movie_recommendation_model.pkl`로 저장됨

## 📊 데이터 소스

모든 데이터는 `../data_scraping/data/` 폴더에서 로드됩니다:

1. **movie_info_watcha.txt**: 영화 기본 정보
   - 영화 ID, 제목, 연도, 장르, 국가, 러닝타임, 관람등급
   - 출연진, 줄거리, 평균 평점, 인기도, 리뷰 수

2. **custom_movie_rating.txt**: 사용자 평점 데이터
   - 사용자 ID, 영화 ID, 영화 제목, 평점

3. **movie_comments.txt**: 영화 리뷰 데이터
   - 영화 ID, 리뷰 ID, 리뷰 내용, 평점, 글자 수

## 🔧 주요 알고리즘

### Matrix Factorization (SVD)
```python
# SVD를 이용한 행렬 분해
U, sigma, Vt = svds(matrix_centered, k=50)
predicted_ratings = np.dot(np.dot(U, sigma), Vt) + user_ratings_mean
```

### TF-IDF + Cosine Similarity
```python
# 영화 컨텐츠 벡터화
tfidf = TfidfVectorizer(max_features=5000)
tfidf_matrix = tfidf.fit_transform(df_movies['content'])

# 유사도 계산
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
```

### Hybrid Recommendation
```python
# 협업 필터링 + 컨텐츠 기반 필터링 결합
hybrid_score = cf_weight * cf_score + cb_weight * cb_score
```

## 📈 모델 평가 지표

- **RMSE (Root Mean Squared Error)**: 예측 평점과 실제 평점의 오차
- **MAE (Mean Absolute Error)**: 절대 오차의 평균
- **Sparsity**: 평점 행렬의 희소성

## 💡 추천 함수 사용 예시

### 협업 필터링 기반 추천
```python
recommendations = recommend_movies_for_user(
    user_id='user_123', 
    predicted_df=predicted_ratings, 
    df_ratings=df_ratings_filtered, 
    df_movies=df_movies, 
    n_recommendations=10
)
```

### 컨텐츠 기반 추천
```python
similar_movies = content_based_recommendations(
    movie_title='기생충', 
    df_movies=df_movies, 
    cosine_sim=cosine_sim, 
    n_recommendations=10
)
```

### 하이브리드 추천
```python
hybrid_recs = hybrid_recommendations(
    user_id='user_123', 
    predicted_df=predicted_ratings, 
    df_ratings=df_ratings_filtered, 
    df_movies=df_movies, 
    cosine_sim=cosine_sim, 
    n_recommendations=10,
    cf_weight=0.6,  # 협업 필터링 가중치
    cb_weight=0.4   # 컨텐츠 기반 필터링 가중치
)
```

## 🔍 향후 개선 사항

1. **딥러닝 모델 적용**
   - Neural Collaborative Filtering (NCF)
   - Autoencoder 기반 추천

2. **추가 특성 활용**
   - 영화 리뷰 감성 분석
   - 시간적 특성 (최신성, 트렌드)
   - 배우/감독 정보 활용

3. **평가 지표 다양화**
   - Precision@K, Recall@K
   - NDCG (Normalized Discounted Cumulative Gain)
   - Diversity, Novelty 측정

4. **실시간 추천**
   - 온라인 학습 구현
   - API 서버 구축

## 📝 참고 자료

- [Collaborative Filtering](https://en.wikipedia.org/wiki/Collaborative_filtering)
- [Matrix Factorization Techniques](https://datajobs.com/data-science-repo/Recommender-Systems-[Netflix].pdf)
- [Content-Based Filtering](https://en.wikipedia.org/wiki/Recommender_system#Content-based_filtering)
- [Hybrid Recommender Systems](https://www.sciencedirect.com/science/article/abs/pii/S0957417406001636)

## 🤝 기여

문제가 발견되거나 개선 사항이 있다면 Issue를 등록하거나 Pull Request를 보내주세요!

