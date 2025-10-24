긁어온 데이터 (data_scraping)을 바탕으로 모델을 만들고 실험하고 있습니다.

# 설정 관리

모든 모델의 하이퍼파라미터와 설정은 `models/config.yaml` 파일에서 관리됩니다.

```yaml
# config.yaml 예시
svd:
  n_factors: 15
  n_epochs: 10
  min_user_ratings: 30
  ...

item_based:
  min_user_ratings: 30
  min_movie_ratings: 10
  top_k: 50
  ...
```

# 추천 시스템 모델

## 1. SVD (Singular Value Decomposition)
협업 필터링 기반 사용자-영화 평점 예측 모델

### 실행 방법
```bash
cd modeling
python run_svd_pipeline.py
```

### 주요 기능
- 사용자 맞춤 영화 추천
- 평점 예측
- Train/Test 분할 및 평가 (RMSE, MAE)
- 모델 저장/로드

### 사용 예시
```python
from models.svd import SVDRecommenderPipeline

# 모델 로드
pipeline = SVDRecommenderPipeline.load('models/pkls/trained_svd_pipeline.pkl')

# 추천
recommendations = pipeline.recommend_for_user(user_id='your_user_id', top_n=10)
```

## 2. Item-Based Collaborative Filtering
아이템 간 유사도 기반 추천 모델

### 실행 방법
```bash
cd modeling
python run_item_based_pipeline.py
```

### 주요 기능
- 특정 영화와 유사한 영화 추천
- 코사인 유사도 기반 아이템 간 유사도 계산
- Top-K 유사도 최적화 (메모리 효율성)
- 모델 저장/로드

### 사용 예시
```python
from models.item_based import ItemBasedRecommender

# 모델 로드
recommender = ItemBasedRecommender.load('models/pkls/trained_item_based.pkl')

# 영화 제목으로 추천
recommendations = recommender.recommend_by_title('기생충', top_n=10, return_scores=True)

# 영화 ID로 추천
recommendations = recommender.recommend('mdRL4eL', top_n=10, return_scores=True)
```

### 설정 파일 (config.yaml)
```yaml
item_based:
  min_user_ratings: 30  # 최소 사용자 평점 수
  min_movie_ratings: 10 # 최소 영화 평점 수
  top_k: 50             # 각 영화당 유지할 상위 K개의 유사 영화
  verbose: true         # 상세 로그 출력
```

### 프로그래밍 방식으로 설정 로드
```python
from models.item_based import ItemBasedConfig

# YAML에서 로드
config = ItemBasedConfig.from_yaml()  # 기본 경로: models/config.yaml

# 또는 직접 생성
config = ItemBasedConfig(min_user_ratings=30, min_movie_ratings=10, top_k=50)
```

# 실험 결과 업데이트

