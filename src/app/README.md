# 영화 추천 시스템 - FastAPI 앱

FastAPI를 통해 영화 추천 서비스를 제공하는 백엔드 애플리케이션입니다.

## 주요 기능

### 1. 사용자 기반 추천 (User-Based Recommendation)
- SVD 기반 협업 필터링을 사용한 개인화 추천
- 사용자의 과거 평점 데이터를 분석하여 맞춤형 영화 추천
- REST API: `GET /users/{user_id}/recommendations`

### 2. 영화 기반 추천 (Movie-Based Recommendation)
- Item-Based Collaborative Filtering 사용
- 코사인 유사도 기반 Top-K 추천 알고리즘
- REST API: `GET /movies/{movie_id}/similar`

### 3. 영화 검색
- 영화 제목으로 검색
- REST API: `GET /movies/search?query={query}`

### 4. 자연어 검색 (Natural Language Search)
- NER(Named Entity Recognition)을 사용한 자연어 검색
- Qwen LLM 기반으로 쿼리에서 배우, 장르, 연도 등을 자동 추출
- 추출된 엔티티를 기반으로 영화 필터링 및 관련성 점수 계산
- REST API: 
  - `GET /api/search/natural-language?query={query}` - 자연어 검색
  - `GET /api/search/extract-entities?query={query}` - 엔티티만 추출 (디버깅용)
- 예시 쿼리:
  - "이병헌이 출연한 액션 영화 추천해줘"
  - "2020년 로맨스 영화"
  - "박찬욱 감독의 스릴러 영화"

### 5. 웹 UI
- Jinja2 템플릿 기반 간단한 웹 인터페이스 제공
- `GET /` - 메인 페이지 (영화 검색, 추천 기능 포함)

## 실행 방법

### 사전 준비

1. **학습된 모델 파일이 필요합니다:**
   ```bash
   # SVD 모델 학습
   cd modeling
   python run_svd_pipeline.py
   
   # Item-Based 모델 학습
   python run_item_based_pipeline.py
   ```

2. **필요한 패키지 설치:**
   ```bash
   pip install -r requirements.txt
   ```

3. **데이터 파일 확인:**
   - `data_scraping/ml-32m/` 폴더에 MovieLens 데이터셋이 있어야 합니다.
   - `modeling/models/pkls/` 폴더에 학습된 모델 파일이 있어야 합니다.

### 로컬 실행

```bash
# 방법 1: Python 모듈로 실행
python -m app.main

# 방법 2: 직접 실행
python app/main.py

# 방법 3: uvicorn 직접 사용
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

기본적으로 `http://0.0.0.0:8000` 또는 `http://localhost:8000`에서 서버가 실행됩니다.

## API 엔드포인트

### Health Check
- `GET /health` - 서버 상태 및 모델 로드 확인

### 영화 검색
- `GET /movies/search?query={query}&limit={limit}`
  - 예: `/movies/search?query=toy%20story&limit=10`

### 사용자 기반 추천
- `GET /users/{user_id}/recommendations?top_n={top_n}`
  - 예: `/users/123/recommendations?top_n=10`

### 영화 기반 유사 영화 추천
- `GET /movies/{movie_id}/similar?top_n={top_n}&genre={genre}&min_year={year}&max_year={year}`
  - 예: `/movies/1/similar?top_n=10&genre=Action`

### 자연어 검색
- `GET /api/search/natural-language?query={query}&limit={limit}&use_ranking={bool}`
  - 예: `/api/search/natural-language?query=이병헌이%20출연한%20액션%20영화&limit=10`
- `GET /api/search/extract-entities?query={query}`
  - 예: `/api/search/extract-entities?query=2020년%20로맨스%20영화`

## 파일 구조

```
app/
├── api.py              # FastAPI 애플리케이션 (엔드포인트 정의)
├── main.py             # 실행 진입점 (uvicorn 실행)
├── modules/
│   ├── core/           # 경로 관리 모듈
│   └── services/       # FastAPI용 서비스 모듈
│       ├── data_access.py        # 데이터 로딩 (Streamlit 없음)
│       └── recommender_service.py # 추천 서비스 (Streamlit 없음)
├── static/             # 정적 파일 (CSS)
│   └── styles.css
├── templates/          # Jinja2 템플릿
│   ├── base.html
│   └── index.html
├── legacy/             # 레거시 Streamlit 앱
│   └── streamlit/
│       ├── app.py      # Streamlit 메인 앱 (레거시)
│       └── modules/   # Streamlit용 모듈들
└── requirements.txt    # 의존성 패키지
```

## 레거시 Streamlit 앱

이전에 사용하던 Streamlit 앱은 `app/legacy/streamlit/` 폴더에 보관되어 있습니다.

### Streamlit 앱 실행 (레거시)
```bash
cd app/legacy/streamlit
streamlit run app.py
```

**참고**: Streamlit 앱은 더 이상 메인 개발 대상이 아니며, 참고용으로만 보관됩니다.

## 개발 환경

- Python 3.8+
- FastAPI 0.115.0+
- uvicorn
- pandas, numpy, scikit-learn 등 (requirements.txt 참조)

## 배포

### 백그라운드 실행 (Cloudflare Tunnel용 - 포트 8501)

#### 1. FastAPI 앱 실행
```bash
# 프로젝트 루트 디렉토리에서 실행
cd /Users/user/Desktop/movie_recommendation

# nohup으로 백그라운드 실행 (포트 8501)
nohup python app/main.py > fastapi.log 2>&1 &

# 프로세스 확인
ps aux | grep uvicorn

# 로그 확인
tail -f fastapi.log

# 프로세스 종료
pkill -f "uvicorn app.api.main:app"
```

#### 2. Cloudflare Tunnel 조회 및 관리
```bash
# Tunnel 목록 조회
cloudflared tunnel list

# 특정 Tunnel 상세 정보 조회
cloudflared tunnel info my-streamlit-tunnel

# Tunnel 상태 확인
cloudflared tunnel info my-streamlit-tunnel --output json
```

#### 3. Cloudflare Tunnel 실행
```bash
# Cloudflare Tunnel 실행 (포그라운드)
cloudflared tunnel run my-streamlit-tunnel

# Cloudflare Tunnel 백그라운드 실행
nohup cloudflared tunnel run my-streamlit-tunnel > cloudflared.log 2>&1 &

# Cloudflare Tunnel 프로세스 확인
ps aux | grep cloudflared

# Cloudflare Tunnel 로그 확인
tail -f cloudflared.log

# Cloudflare Tunnel 종료
pkill -f "cloudflared tunnel"
```

#### 4. 전체 배포 프로세스 (한 번에 실행)
```bash
# 프로젝트 루트 디렉토리에서 실행
cd /Users/user/Desktop/movie_recommendation

# 1. FastAPI 앱 백그라운드 실행
nohup python app/main.py > fastapi.log 2>&1 &

# 2. Cloudflare Tunnel 백그라운드 실행
nohup cloudflared tunnel run my-streamlit-tunnel > cloudflared.log 2>&1 &

# 3. 프로세스 확인
ps aux | grep -E "(uvicorn|cloudflared)" | grep -v grep

# 4. 로그 확인
tail -f fastapi.log      # FastAPI 로그
tail -f cloudflared.log  # Cloudflare Tunnel 로그
```

#### 5. macOS 시스템 잠금 방지 (시스템이 잠들어도 계속 실행)

macOS에서 시스템이 잠들어도 Cloudflare Tunnel이 계속 실행되도록 하는 방법:

**방법 1: caffeinate 사용 (간단한 방법)**
```bash
# caffeinate로 시스템이 잠들지 않게 하면서 실행
caffeinate -d cloudflared tunnel run my-streamlit-tunnel

# 백그라운드 실행
nohup caffeinate -d cloudflared tunnel run my-streamlit-tunnel > cloudflared.log 2>&1 &
```

**방법 2: launchd 서비스로 등록 (권장 - 재부팅 후에도 자동 실행)**

1. launchd plist 파일 생성:
```bash
# plist 파일 생성
cat > ~/Library/LaunchAgents/com.cloudflare.tunnel.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>my-streamlit-tunnel</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/user/Desktop/movie_recommendation/cloudflared.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/user/Desktop/movie_recommendation/cloudflared.log</string>
</dict>
</plist>
EOF
```

2. 서비스 로드 및 시작:
```bash
# 서비스 로드
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.plist

# 서비스 시작
launchctl start com.cloudflare.tunnel

# 서비스 상태 확인
launchctl list | grep cloudflare

# 서비스 중지
launchctl stop com.cloudflare.tunnel

# 서비스 언로드 (완전 제거)
launchctl unload ~/Library/LaunchAgents/com.cloudflare.tunnel.plist
```

**참고:**
- `caffeinate -d`: 디스플레이가 잠들지 않게 함 (배터리 소모 주의)
- `launchd`: 시스템 서비스로 등록하여 재부팅 후에도 자동 실행
- plist 파일의 경로(`/opt/homebrew/bin/cloudflared`)는 실제 cloudflared 설치 경로에 맞게 수정 필요
  - 확인: `which cloudflared`
- Cloudflare Tunnel 설정 파일: `~/.cloudflared/config.yml`
- Tunnel 이름: `my-streamlit-tunnel`
- 로컬 포트: `8501`
- 도메인: `movie.mingyuprojects.dev`

### 프로덕션 환경
```bash
# Gunicorn과 함께 실행 (권장)
gunicorn app.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker (선택사항)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 문제 해결

### 모델 파일이 없다는 에러
- `modeling/models/pkls/` 폴더에 학습된 모델 파일이 있는지 확인
- `run_svd_pipeline.py`와 `run_item_based_pipeline.py` 실행

### 데이터 파일이 없다는 에러
- `data_scraping/ml-32m/` 폴더에 MovieLens 데이터셋이 있는지 확인
- 필요한 파일: `movies.csv`, `ratings.csv` 등

### 포트 충돌
- 기본 포트(8000)가 사용 중이면 `--port` 옵션으로 변경
- 예: `uvicorn app.api:app --port 8080`
