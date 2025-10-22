# 🎬 영화 추천 시스템 (Movie Recommendation System)

Watcha 데이터를 활용한 영화 추천 시스템 Streamlit 앱입니다.

## ✨ 주요 기능

### 1. 🎯 사용자 기반 추천 (User-based Recommendation)
- SVD(Singular Value Decomposition) 기반 협업 필터링
- 사용자의 과거 평점 데이터를 분석하여 맞춤형 영화 추천

### 2. 🎞️ 영화 기반 추천 (Movie-based Recommendation)
- **컨텐츠 기반**: 장르와 줄거리의 TF-IDF 유사도를 활용
- **협업 필터링 기반**: 사용자 평점 패턴의 코사인 유사도를 활용
- 좋아하는 영화와 비슷한 영화를 발견

### 3. ✨ 하이브리드 추천 (Hybrid Recommendation)
- 협업 필터링과 컨텐츠 기반 추천을 결합
- 가중치 조절을 통한 맞춤형 추천
- 두 방식의 장점을 결합한 고급 추천 시스템

## 📊 데이터

- **영화 정보**: 13,000+ 영화
- **사용자 평점**: 900,000+ 평점 데이터
- **사용자 수**: 1,100+ 명
- **데이터 출처**: Watcha (왓챠)

## 🚀 로컬 실행 방법

### 1. 저장소 클론 또는 다운로드

```bash
cd /path/to/movie_recommendation
```

### 2. 가상환경 생성 및 활성화

```bash
# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 필요한 패키지 설치

```bash
cd app
pip install -r requirements.txt
```

### 4. Streamlit 앱 실행

```bash
streamlit run streamlit_app.py
```

브라우저에서 자동으로 `http://localhost:8501` 이 열립니다.

## 🌐 Streamlit Cloud에 배포하기

### 1. GitHub 저장소 준비

1. GitHub에 새 저장소를 만듭니다
2. 프로젝트를 푸시합니다:

```bash
cd /path/to/movie_recommendation
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/movie-recommendation.git
git push -u origin main
```

### 2. Streamlit Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io)에 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. 저장소 선택:
   - Repository: `your-username/movie-recommendation`
   - Branch: `main`
   - Main file path: `app/streamlit_app.py`
5. "Deploy!" 클릭

### 3. 배포 설정

**중요**: 데이터 파일이 큰 경우 GitHub LFS(Large File Storage)를 사용하거나, 
클라우드 스토리지(AWS S3, Google Cloud Storage 등)에 업로드하고 
앱에서 다운로드하도록 수정해야 할 수 있습니다.

#### 데이터 파일 크기가 큰 경우:

```python
# streamlit_app.py 상단에 추가
import urllib.request

@st.cache_data
def download_data_if_needed():
    if not Path('../data_scraping/data/movie_info_watcha.txt').exists():
        # 클라우드 스토리지에서 다운로드
        urllib.request.urlretrieve(
            'https://your-storage-url/movie_info_watcha.txt',
            '../data_scraping/data/movie_info_watcha.txt'
        )
```

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Machine Learning**: 
  - Scikit-learn (TF-IDF, Cosine Similarity)
  - Scipy (SVD, Sparse Matrix)
  - NumPy, Pandas
- **추천 알고리즘**:
  - Matrix Factorization (SVD)
  - Content-based Filtering (TF-IDF)
  - Item-based Collaborative Filtering
  - Hybrid Recommendation

## 📁 프로젝트 구조

```
app/
├── streamlit_app.py         # 메인 앱 파일
├── requirements.txt          # 패키지 의존성
├── README.md                 # 이 파일
└── utils/
    ├── data_loader.py        # 데이터 로딩 유틸리티
    └── recommender.py        # 추천 시스템 클래스
```

## ⚙️ 성능 최적화

### 캐싱 활용
- `@st.cache_data`: 데이터 로딩 캐싱
- `@st.cache_resource`: 모델 학습 캐싱 (최초 1회만 실행)

### 메모리 최적화
- Sparse Matrix 사용으로 메모리 효율성 향상
- 필터링을 통한 Cold Start 문제 해결

## 🐛 문제 해결 (Troubleshooting)

### 데이터 로딩 오류
```
FileNotFoundError: [Errno 2] No such file or directory
```
**해결방법**: 데이터 파일 경로를 확인하고, `data_loader.py`의 `data_path`를 수정하세요.

### 메모리 부족 오류
```
MemoryError: Unable to allocate array
```
**해결방법**: `data_loader.py`의 필터링 파라미터를 조정하여 데이터 크기를 줄이세요.
- `min_user_ratings`를 50으로 증가
- `min_movie_ratings`를 20으로 증가

### Streamlit Cloud 배포 실패
- 데이터 파일이 GitHub 용량 제한(100MB)을 초과하는 경우
- **해결방법**: Git LFS 사용 또는 외부 스토리지 활용

## 📝 라이선스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트, 기능 제안, 풀 리퀘스트를 환영합니다!

## 📧 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 등록해주세요.

---

**Made with ❤️ using Streamlit**

