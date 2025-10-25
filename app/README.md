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


# 서비스 서빙

## Cloudflare 도메인 연결 및 로컬 실행

### 1. Cloudflare 도메인 설정
1. Cloudflare에서 구매한 도메인을 Cloudflare DNS에 연결
2. DNS 레코드 설정:
   - Type: A
   - Name: @ (루트 도메인) 또는 원하는 서브도메인
   - IPv4 address: 로컬 IP 주소 (예: 192.168.1.100)
   - Proxy status: DNS only (주황색 구름 비활성화)

### 2. 로컬 Streamlit 실행
```bash
# 앱 디렉토리로 이동
cd app

# Streamlit 실행 (포트 8501)
streamlit run streamlit_app.py --server.port 8501
```

#### 배포할 떄 사용하는 명령어

```bash
nohup cloudflared tunnel run my-streamlit-tunnel > ~/cloudflared.log 2>&1 &
nohup streamlit run app.py > ~/streamlit.log 2>&1 &
nohup caffeinate > /dev/null 2>&1 &
```

- 💡 맥 절전 X
- 🌐 Cloudflare 항상 연결
- 🧠 Streamlit 지속 실행
- 🔒 터미널 닫아도 계속 유지


### 3. 포트 포워딩 설정 (macOS)
```bash
# Cloudflare Tunnel 사용 (권장)
# 1. Cloudflare Tunnel 설치
brew install cloudflared

# 2. Cloudflare에 로그인
cloudflared tunnel login

# 3. 터널 생성
cloudflared tunnel create movie-recommendation

# 4. 터널 실행
cloudflared tunnel --url http://localhost:8501 run movie-recommendation

# 5. DNS 라우팅 설정 (터널을 도메인에 연결)
cloudflared tunnel route dns my-streamlit-tunnel movie.mingyuprojects.dev

# 6. 터널 실행
cloudflared tunnel run my-streamlit-tunnel

# 7. 터널 조회
cloudflared tunnel list

# 또는 ngrok 사용
brew install ngrok
ngrok http 8501
```

### 4. 방화벽 설정 (macOS)
```bash
# 방화벽에서 포트 8501 허용
sudo pfctl -f /etc/pf.conf
```

### 5. 라우터 포트 포워딩
라우터 관리 페이지에서:
- 외부 포트: 8501 (또는 원하는 포트)
- 내부 IP: 맥의 로컬 IP
- 내부 포트: 8501
- 프로토콜: TCP

