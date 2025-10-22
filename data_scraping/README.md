# 데이터 스크래핑 모듈

왓챠 피디아에서 데이터를 긁어오고 있습니다.

## 수집 데이터

### 1. 영화 기본 정보 (`movie_info_watcha.txt`)
- 영화 제목, 장르, 감독, 출연진
- 평점, 개봉일, 러닝타임
- 포스터 이미지 URL

### 2. 사용자 코멘트 (`movie_comments.txt`)
- 영화별 사용자 댓글
- 댓글 작성자, 작성일
- 댓글 내용 및 감정 분석

### 3. 사용자별 영화 평점 (`custom_movie_rating.txt`)
- 사용자 ID별 영화 평점 데이터
- 평점 값 (1-5점)
- 평가 일시

## 스크래핑 로직

### 기술 스택
- **Playwright**: 브라우저 자동화
- **BeautifulSoup4**: HTML 파싱
- **Pandas**: 데이터 처리 및 저장

### 수집 과정
1. **로그인**: 왓챠 계정으로 자동 로그인
2. **영화 목록 탐색**: 카테고리별 영화 리스트 수집
3. **상세 정보 수집**: 각 영화의 상세 페이지 방문
4. **댓글 수집**: 영화별 사용자 댓글 크롤링
5. **평점 수집**: 사용자별 영화 평점 데이터 수집

### 실행 방법

```bash
# 전체 데이터 수집
python run_all.py

# 개별 수집
python run_movie_info.py      # 영화 기본 정보
python run_movie_comments.py  # 영화 댓글
python run_custom_rating.py   # 사용자 평점
```

### 디렉토리 구조
```
data_scraping/
├── common/           # 공통 유틸리티
├── scrapers/         # 스크래퍼 클래스
├── data/            # 수집된 데이터
├── debug/           # 디버깅 스크립트
└── legacy/          # 레거시 코드
```

