# 🚀 배포 가이드

## 📋 목차
1. [로컬에서 테스트하기](#로컬에서-테스트하기)
2. [Streamlit Cloud에 배포하기](#streamlit-cloud에-배포하기)
3. [기타 배포 옵션](#기타-배포-옵션)

---

## 🖥️ 로컬에서 테스트하기

### Step 1: 패키지 설치

```bash
# 프로젝트 루트에서
cd app

# 가상환경 생성 (선택사항이지만 권장)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### Step 2: 앱 실행

```bash
streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501` 로 자동으로 열립니다.

### Step 3: 앱 테스트

1. **사용자 기반 추천** 탭에서 사용자를 선택하고 추천을 받아보세요
2. **영화 기반 추천** 탭에서 좋아하는 영화를 검색하고 비슷한 영화를 찾아보세요
3. **하이브리드 추천** 탭에서 가중치를 조절하며 추천을 받아보세요

---

## ☁️ Streamlit Cloud에 배포하기

Streamlit Cloud는 **무료**로 Streamlit 앱을 배포할 수 있는 가장 쉬운 방법입니다!

### Step 1: GitHub 저장소 생성

1. [GitHub](https://github.com)에 로그인
2. 새 저장소 생성 (New repository)
   - Repository name: `movie-recommendation` (또는 원하는 이름)
   - Public 또는 Private 선택
   - README 체크 해제 (이미 있음)

### Step 2: 코드 푸시

```bash
# 프로젝트 루트에서
cd /Users/visuworks/Desktop/movie_recommendation

# Git 초기화 (아직 안했다면)
git init

# .gitignore 추가
echo "
# Python
__pycache__/
*.pyc
venv/
.DS_Store
.streamlit/
*.egg-info/

# IDE
.vscode/
.idea/
" > .gitignore

# 모든 파일 추가
git add .

# 커밋
git commit -m "Add Streamlit movie recommendation app"

# GitHub 저장소 연결 (본인의 username과 repo로 변경)
git remote add origin https://github.com/YOUR_USERNAME/movie-recommendation.git

# 메인 브랜치로 변경
git branch -M main

# 푸시
git push -u origin main
```

### Step 3: Streamlit Cloud 설정

1. [share.streamlit.io](https://share.streamlit.io) 접속
2. **"Sign in with GitHub"** 클릭하여 로그인
3. **"New app"** 클릭
4. 설정:
   ```
   Repository: YOUR_USERNAME/movie-recommendation
   Branch: main
   Main file path: app/streamlit_app.py
   ```
5. **"Advanced settings"** (선택사항):
   - Python version: 3.9 이상
6. **"Deploy!"** 클릭

### Step 4: 배포 확인

- 배포가 완료되면 (약 3-5분 소요) 자동으로 URL이 생성됩니다
- URL 형식: `https://your-username-movie-recommendation-app-streamlit-app-xxxxx.streamlit.app`
- 이 URL을 통해 누구나 앱에 접근할 수 있습니다!

### ⚠️ 주의사항: 데이터 파일 크기

GitHub는 파일당 **100MB** 제한이 있습니다. 만약 데이터 파일이 이보다 크다면:

#### 옵션 1: Git LFS 사용

```bash
# Git LFS 설치
brew install git-lfs  # Mac
# 또는
git lfs install

# 큰 파일 추적
git lfs track "data_scraping/data/*.txt"
git add .gitattributes
git add data_scraping/data/*.txt
git commit -m "Add large data files with LFS"
git push
```

#### 옵션 2: 외부 스토리지 사용

데이터를 Google Drive, Dropbox, AWS S3 등에 업로드하고 앱에서 다운로드:

```python
# streamlit_app.py에 추가
import requests
from pathlib import Path

@st.cache_data
def download_data():
    data_dir = Path('../data_scraping/data')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    files = {
        'movie_info_watcha.txt': 'YOUR_DOWNLOAD_URL_1',
        'custom_movie_rating.txt': 'YOUR_DOWNLOAD_URL_2'
    }
    
    for filename, url in files.items():
        filepath = data_dir / filename
        if not filepath.exists():
            st.info(f"Downloading {filename}...")
            response = requests.get(url)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            st.success(f"{filename} downloaded!")

# main() 시작 부분에 추가
download_data()
```

---

## 🌐 기타 배포 옵션

### 1. Heroku

```bash
# Procfile 생성
echo "web: streamlit run app/streamlit_app.py --server.port=$PORT" > Procfile

# runtime.txt 생성
echo "python-3.9.16" > runtime.txt

# Heroku 배포
heroku create your-app-name
git push heroku main
```

### 2. Docker + AWS/GCP

```dockerfile
# Dockerfile 생성
FROM python:3.9-slim

WORKDIR /app
COPY app/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501"]
```

```bash
# Docker 빌드 및 실행
docker build -t movie-recommendation .
docker run -p 8501:8501 movie-recommendation
```

### 3. Railway

1. [Railway.app](https://railway.app) 접속
2. "New Project" → "Deploy from GitHub repo"
3. 저장소 선택
4. 자동으로 배포됨

---

## 🔧 배포 후 설정

### 커스텀 도메인 연결 (Streamlit Cloud)

1. Streamlit Cloud 대시보드에서 앱 선택
2. "Settings" → "Custom domain" 클릭
3. 본인의 도메인 입력 (예: `movie-rec.yourdomain.com`)
4. DNS 설정에서 CNAME 레코드 추가

### 환경 변수 설정

민감한 정보(API 키 등)가 있다면:

1. Streamlit Cloud 대시보드 → 앱 선택
2. "Settings" → "Secrets" 클릭
3. TOML 형식으로 추가:

```toml
# .streamlit/secrets.toml
api_key = "your-secret-key"
database_url = "your-db-url"
```

앱에서 사용:

```python
import streamlit as st
api_key = st.secrets["api_key"]
```

---

## 📊 모니터링 및 유지보수

### 로그 확인

Streamlit Cloud에서:
1. 앱 대시보드 → "Logs" 탭
2. 실시간 로그 확인 가능

### 앱 업데이트

```bash
# 코드 수정 후
git add .
git commit -m "Update feature"
git push

# Streamlit Cloud가 자동으로 재배포합니다!
```

### 성능 최적화

1. **캐싱 활용**: `@st.cache_data`, `@st.cache_resource` 적극 활용
2. **데이터 크기 줄이기**: 필요한 데이터만 로드
3. **로딩 시간 개선**: 초기 로딩에 시간이 걸린다면 프리로딩 고려

---

## ❓ 문제 해결

### 배포 실패 시

1. **requirements.txt 확인**
   - 패키지 버전이 호환되는지 확인
   - `pip freeze > requirements.txt`로 재생성

2. **파일 경로 확인**
   - 상대 경로 사용 (`../data_scraping/data/`)
   - Windows/Mac/Linux 호환성 확인

3. **메모리 부족**
   - 데이터 필터링 강화
   - Sparse matrix 활용
   - 모델 크기 줄이기

### 앱이 느릴 때

1. 캐싱 제대로 작동하는지 확인
2. 데이터 샘플링 고려
3. 최적화된 알고리즘 사용

---

## 🎉 완료!

이제 영화 추천 시스템이 전 세계에 공개되었습니다!

URL을 친구들과 공유하고 피드백을 받아보세요 🚀

**예시 URL**: `https://movie-recommendation.streamlit.app`

