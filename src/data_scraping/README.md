# 데이터 로딩 모듈

## 데이터 소스

현재 프로젝트는 **ML-32M (MovieLens 32M)** 데이터셋을 사용합니다.
- 87,585개의 영화
- 32,000,204개의 평점
- 200,948명의 사용자

### 데이터 형식

#### 영화 정보 (`ml-32m/movies.csv`)
- `movieId`: 영화 ID
- `title`: 영화 제목 (연도 포함)
- `genres`: 장르 (pipe-separated)

#### 평점 데이터 (`ml-32m/ratings.csv`)
- `userId`: 사용자 ID
- `movieId`: 영화 ID
- `rating`: 평점 (0.5 ~ 5.0)
- `timestamp`: 타임스탬프

## 레거시 데이터 (법적 위험으로 인해 미사용)

와챠피디아 크롤링 데이터는 법적 위험 때문에 더 이상 사용하지 않습니다.
관련 코드는 `legacy/` 디렉토리로 이동되었습니다.

### 디렉토리 구조
```
data_scraping/
├── common/           # 공통 유틸리티
│   ├── data_loader.py      # ML-32M 데이터 로더
│   ├── exceptions.py       # 예외 클래스
│   └── logger.py           # 로깅 유틸리티
├── ml-32m/          # ML-32M 데이터셋
├── legacy/          # 레거시 코드 (와챠 크롤링 관련, 미사용)
│   ├── config.py           # 왓챠피디아 설정
│   ├── browser_manager.py  # 브라우저 관리
│   ├── data_storage.py     # 데이터 저장
│   ├── data_cleaner.py     # 데이터 정제
│   └── scrapers/           # 스크래퍼 클래스
└── data/            # 로컬 테스트 데이터
```

