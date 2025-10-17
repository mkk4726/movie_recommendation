# Movie Recommendation System

영화 추천 시스템 프로젝트입니다.

## 프로젝트 소개

Watcha에서 영화 데이터를 수집하고 분석하여 사용자에게 맞춤형 영화를 추천하는 시스템입니다.

## 프로젝트 구조

```
movie_recommendation/
├── data_scraping/          # 데이터 스크래핑 모듈
│   ├── common/            # 공통 유틸리티
│   ├── scrapers/          # 스크래퍼 클래스
│   ├── data/              # 수집된 데이터
│   └── README.md          # 스크래핑 상세 문서
├── pyproject.toml         # Poetry 의존성 관리
├── requirements.txt       # pip 의존성
└── README.md             # 메인 문서
```

## 시작하기

### 1. 의존성 설치

Poetry 사용:
```bash
poetry install
```

또는 pip 사용:
```bash
pip install -r requirements.txt
pip install playwright pandas beautifulsoup4 lxml
playwright install chromium
```

### 2. 데이터 수집

전체 데이터 수집 파이프라인 실행:
```bash
cd data_scraping
python run_all.py
```

자세한 사용법은 [data_scraping/README.md](data_scraping/README.md)를 참조하세요.

## 주요 기능

### 데이터 스크래핑 (완료)
- ✅ 영화 기본 정보 수집
- ✅ 사용자 코멘트 및 평점 수집
- ✅ 사용자별 영화 평점 수집
- ✅ 리팩토링된 모듈화 구조
- ✅ 체계적인 에러 핸들링 및 로깅

### 데이터 분석 (예정)
- 영화 데이터 전처리
- 사용자 선호도 분석
- 영화 유사도 계산

### 추천 시스템 (예정)
- 협업 필터링 기반 추천
- 콘텐츠 기반 추천
- 하이브리드 추천 시스템

## 개발 정보

### 최근 업데이트 (2025-10-17)

**데이터 스크래핑 모듈 리팩토링**
- 함수 기반에서 클래스 기반 객체지향 구조로 전환
- 공통 모듈 분리 (Config, BrowserManager, DataCleaner, DataStorage)
- CSV 형식의 데이터 저장으로 변경 (기존 TXT 대신)
- 체계적인 예외 처리 및 로깅 시스템 추가
- 타입 힌트 및 Docstring 문서화
- 중복 코드 제거 및 DRY 원칙 적용

### 기술 스택

- **언어**: Python 3.10+
- **웹 스크래핑**: Playwright, BeautifulSoup4, lxml
- **데이터 처리**: Pandas
- **의존성 관리**: Poetry
- **예정**: LangChain, Streamlit (추천 시스템 구현시)

## 기여

이슈나 개선 제안은 GitHub Issues를 통해 제출해 주세요.

## 라이센스

이 프로젝트는 학습 목적으로 제작되었습니다.
