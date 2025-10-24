# 영화 추천 시스템 Streamlit 앱

Streamlit을 통해 영화 추천 서비스를 배포하고 있습니다.

## 배포 링크

- 관리자 페이지: https://share.streamlit.io/?utm_source=streamlit&utm_medium=referral&utm_campaign=main&utm_content=-ss-streamlit-io-topright
- 배포 페이지: https://movie-recommendation-by-watcha.streamlit.app/

## 주요 기능

### 1. 사용자 기반 추천 (User-Based Recommendation)
- SVD 기반 협업 필터링을 사용한 개인화 추천
- 사용자의 과거 평점 데이터를 분석하여 맞춤형 영화 추천
- 사용자가 높게 평가한 영화와 AI 추천 영화를 함께 표시

### 2. 영화 기반 추천 (Movie-Based Recommendation)
좋아하는 영화와 비슷한 영화를 찾아주는 기능입니다.

#### Item-Based Collaborative Filtering
- 사용자들의 평점 패턴을 분석하여 영화 간 유사도 계산
- 같은 영화들을 좋아하는 사용자들이 함께 좋아하는 영화 추천
- 코사인 유사도 기반 Top-K 추천 알고리즘 사용
- 메모리 효율적인 희소 행렬(Sparse Matrix) 구조

## 실행 방법

### 사전 준비
1. 학습된 모델 파일이 필요합니다:
   ```bash
   # SVD 모델 학습
   cd modeling
   python run_svd_pipeline.py
   
   # Item-Based 모델 학습
   python run_item_based_pipeline.py
   ```

2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

### 로컬 실행
```bash
cd app
streamlit run streamlit_app.py
```

## 파일 구조

- `streamlit_app.py`: 메인 애플리케이션
- `streamlit_recommender.py`: 추천 시스템 래퍼 (Streamlit 캐싱 적용)
- `streamlit_data_loader.py`: 데이터 로더 (Streamlit 캐싱 적용)
- `requirements.txt`: 필요한 패키지 목록