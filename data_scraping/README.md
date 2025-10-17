# Movie Data Scraping

Watcha 영화 정보, 코멘트, 사용자 평점을 스크래핑하는 리팩토링된 프로젝트입니다.

## 프로젝트 구조

```
data_scraping/
├── common/                  # 공통 유틸리티 모듈
│   ├── __init__.py
│   ├── config.py           # 설정 관리
│   ├── browser_manager.py  # Playwright 브라우저 관리
│   ├── data_cleaner.py     # 데이터 정제 유틸리티
│   ├── data_storage.py     # CSV 데이터 저장/로드
│   ├── exceptions.py       # 커스텀 예외
│   └── logger.py           # 로깅 시스템
├── scrapers/               # 스크래퍼 클래스
│   ├── __init__.py
│   ├── base_scraper.py     # 베이스 스크래퍼 클래스
│   ├── movie_info_scraper.py        # 영화 정보 스크래퍼
│   ├── movie_comments_scraper.py    # 영화 코멘트 스크래퍼
│   └── custom_rating_scraper.py     # 사용자 평점 스크래퍼
├── run_movie_info.py       # 영화 정보 스크래핑 실행
├── run_movie_comments.py   # 영화 코멘트 스크래핑 실행
├── run_custom_rating.py    # 사용자 평점 스크래핑 실행
├── run_all.py              # 전체 스크래핑 파이프라인 실행
└── data/                   # 데이터 디렉토리
    ├── movie_info_watcha.txt
    ├── movie_comments.txt
    └── custom_movie_rating.txt
```

## 주요 개선사항

### 1. 모듈화 및 클래스 구조
- **공통 모듈**: 반복되는 로직을 재사용 가능한 모듈로 분리
- **스크래퍼 클래스**: 각 스크래핑 작업을 독립적인 클래스로 구현
- **베이스 클래스**: 공통 기능을 상속받는 구조

### 2. 에러 핸들링
- 구체적인 예외 타입 정의
- 체계적인 로깅 시스템
- 실패한 작업 추적 및 재시도 가능

### 3. 설정 관리
- 모든 설정을 `Config` 클래스에 중앙화
- XPath, URL, 타임아웃 등 쉽게 수정 가능
- 매직 넘버 제거

### 4. 데이터 저장
- TXT 형식 유지 (`/` 구분자)
- 데이터에서 `/` 문자 자동 제거
- Pandas DataFrame과 호환

### 5. 코드 품질
- 타입 힌트 추가
- Docstring 문서화
- 일관된 코딩 스타일
- SRP(Single Responsibility Principle) 준수

## 설치

필요한 패키지를 설치합니다:

```bash
pip install playwright pandas beautifulsoup4 lxml
playwright install chromium
```

## 사용법

### 1. 개별 스크래핑 실행

영화 정보 스크래핑:
```bash
python run_movie_info.py --limit 10 --delay 2
```

영화 코멘트 스크래핑:
```bash
python run_movie_comments.py --limit 5 --delay 2
```

사용자 평점 스크래핑:
```bash
python run_custom_rating.py --limit 5 --delay 2
```

### 2. 전체 파이프라인 실행

모든 스크래핑 작업을 순차적으로 실행:

```bash
python run_all.py --delay 2
```

특정 단계 건너뛰기:
```bash
python run_all.py --skip-movie-info --delay 2
```

### 옵션 설명

- `--limit N`: 스크래핑할 항목 수 제한 (기본: 무제한)
- `--delay N`: 요청 간 대기 시간(초) (기본: 2.0)
- `--skip-movie-info`: 영화 정보 스크래핑 건너뛰기
- `--skip-comments`: 코멘트 스크래핑 건너뛰기
- `--skip-ratings`: 평점 스크래핑 건너뛰기

## Python에서 사용하기

```python
from common import Config, DataStorage
from scrapers import MovieInfoScraper, MovieCommentsScraper

# 설정 생성
config = Config()
storage = DataStorage(config)

# 영화 정보 스크래핑
scraper = MovieInfoScraper(config)
movie_data = scraper.scrape('m2djnad')
storage.save_movie_info(movie_data)

# 데이터 로드
import pandas as pd
df = storage.load_movie_info()
print(df.head())
```

## 설정 커스터마이징

`common/config.py`에서 설정을 수정할 수 있습니다:

```python
from common import Config

config = Config()
config.BROWSER_HEADLESS = False  # 브라우저 UI 표시
config.SCROLL_DELAY = 3          # 스크롤 딜레이 증가
config.LOG_LEVEL = "DEBUG"       # 상세 로깅
```

## 로그 파일

실행 로그는 `scraper.log`에 저장됩니다.

## 데이터 형식

### movie_info_watcha.txt
```
MovieID/Title/Year/Genre/Country/Runtime/Age/Cast_Production/Synopsis/Avg_Rating/N_Rating/N_Comments
```

### movie_comments.txt
```
MovieID/CustomID/Comment/Rating/N_Likes
```

### custom_movie_rating.txt
```
CustomID/MovieID/MovieName/Rating
```

모든 필드에서 `/` 문자는 자동으로 공백으로 대체됩니다.

## 주의사항

1. **Rate Limiting**: 적절한 `--delay` 값을 사용하여 서버에 부담을 주지 않도록 주의
2. **Headless 모드**: 기본적으로 headless 모드로 실행되며, 디버깅시 `Config.BROWSER_HEADLESS = False`로 설정
3. **타임아웃**: 네트워크 상태에 따라 `Config.BROWSER_TIMEOUT` 조정 가능

## 기존 코드와의 차이점

### 이전 (Legacy)
- 함수 기반 구조
- 하드코딩된 XPath와 설정
- `/` 구분자 TXT 파일
- 제한적인 에러 핸들링
- 중복된 코드

### 현재 (Refactored)
- 클래스 기반 객체지향 구조
- 중앙화된 설정 관리
- TXT 형식 (데이터 정제 강화)
- 체계적인 예외 처리 및 로깅
- DRY 원칙 적용

## 라이센스

이 프로젝트는 학습 목적으로 제작되었습니다.
