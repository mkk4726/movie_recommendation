# Legacy Code - 왓챠피디아 크롤링

## 📌 개요

이 디렉토리는 프로젝트 초기에 사용했던 **왓챠피디아 크롤링 코드**를 보관합니다.

**⚠️ 현재 상태: 더 이상 사용하지 않음 (레거시)**

## 📜 히스토리

### 초기 개발

프로젝트 초기에는 한국어 영화 데이터가 풍부한 **왓챠피디아**를 크롤링하여 추천 시스템을 구축했습니다.

- **목적**: 한국어 영화 리뷰/평점 데이터로 콘텐츠 기반 추천 모델 구축
- **성과**: 110만건 이상의 고객-영화 평가 데이터 수집 성공
- **기술 스택**: Selenium → Playwright로 전환, 브라우저 자동화 기반 크롤링
- **최종 업데이트**: 2025년 10월 왓챠피디아 페이지 구조 변경에 맞춰 XPath 선택자 업데이트

### 전환 결정

**법적 위험**으로 인해 데이터 소스를 변경했습니다:

- 🚨 **이용약관 위반**: 웹 크롤링 시 서비스 이용약관 위반 우려
- ⚖️ **저작권 문제**: 스크래핑 데이터의 상업적 활용 제한
- 🔒 **서비스 안정성**: 데이터 소스 플랫폼의 정책 변경에 취약

### 현재 데이터 소스

- **MovieLens ML-32M**: 공개 데이터셋 (87,585개 영화, 3,200만개+ 평점)
- **OMDb API**: 공식 API를 통한 영화 메타데이터 보강 (향후 통합 예정)
- **위치**: `../common/data_loader.py` (ML-32M 데이터 로더)

## 📁 파일 구조

```
legacy/
├── config.py              # 왓챠피디아 설정 (URL, XPath 등)
├── browser_manager.py     # Playwright 브라우저 관리
├── data_storage.py        # TXT 파일 데이터 저장/로드
├── data_cleaner.py        # 수집된 데이터 정제
├── login_watcha.py        # 왓챠 로그인 세션 관리
├── run_all.py             # 전체 크롤링 파이프라인 실행
├── run_movie_info.py      # 영화 정보 크롤링
├── run_movie_comments.py  # 영화 코멘트 크롤링
├── run_custom_rating.py   # 사용자 평점 크롤링
├── scrapers/              # 스크래퍼 클래스
│   ├── base_scraper.py          # 기본 스크래퍼
│   ├── movie_info_scraper.py    # 영화 정보 스크래퍼
│   ├── movie_comments_scraper.py # 코멘트 스크래퍼
│   └── custom_rating_scraper.py  # 평점 스크래퍼
├── old_utils/             # 구버전 유틸리티 (Selenium 기반)
│   ├── selenium_driver.py  # Selenium 드라이버 관리
│   ├── json.py, pickle.py, txt.py  # 데이터 저장 유틸
│   └── re.py               # 정규표현식 유틸
├── assets/                # Chromedriver 바이너리
└── debug/                 # 디버깅 스크립트
```

## 🔧 주요 컴포넌트

### 1. 스크래퍼 (Scrapers)

Playwright 기반 브라우저 자동화로 웹 페이지를 크롤링합니다:

- **MovieInfoScraper**: 영화 제목, 감독, 출연진, 시놉시스, 평점 등
- **MovieCommentsScraper**: 영화별 사용자 코멘트 (최대 500개)
- **CustomRatingScraper**: 사용자별 영화 평점 목록

### 2. 데이터 저장

TXT 파일 기반 저장 (구분자: `/`)

- `movie_info_watcha.txt`: 영화 정보
- `movie_comments.txt`: 영화 코멘트
- `custom_movie_rating.txt`: 사용자 평점

### 3. 실행 스크립트

```bash
# 전체 파이프라인 실행
python run_all.py

# 개별 실행
python run_movie_info.py      # 영화 정보
python run_movie_comments.py  # 코멘트
python run_custom_rating.py   # 평점
```

## 📊 수집 데이터 예시

### 영화 정보
```
movie_id/title/year/genre/country/runtime/age/cast/synopsis/avg_rating/n_rating/n_comments
```

### 영화 코멘트
```
movie_id/user_id/comment/rating/n_likes
```

### 사용자 평점
```
user_id/movie_id/movie_name/rating
```

## ⚠️ 주의사항

### 사용 금지

이 코드는 **더 이상 사용하지 않습니다**:
- 실제 크롤링 실행 금지
- 법적 리스크 있음
- 왓챠피디아 페이지 구조가 변경되어 동작 안 할 수 있음

### 보관 목적

- **참고용**: 브라우저 자동화 크롤링 구현 참고
- **학습용**: Playwright, XPath 선택자, 데이터 정제 패턴 예시
- **기록용**: 프로젝트 히스토리 보존

## 🔗 관련 문서

- 상위 디렉토리: `../README.md` - 현재 데이터 소스 (ML-32M)
- 메인 README: `../../README.md` - 전체 프로젝트 구조

## 📝 기술적 세부사항

### XPath 기반 스크래핑
- 왓챠피디아 페이지 구조 분석하여 XPath 선택자 작성
- 2025년 10월 페이지 구조 변경에 맞춰 업데이트

### 인증 관리
- `login_watcha.py`로 세션 저장/복원
- 쿠키 기반 인증으로 로그인 상태 유지

### 데이터 정제
- 특수문자(`/`) 제거하여 구분자 충돌 방지
- 한글, 이모지 등 인코딩 처리

## 🎓 배운 점

1. **법적 이슈**: 웹 크롤링 시 이용약관 및 저작권 고려 필수
2. **데이터 소스 안정성**: 공식 API나 공개 데이터셋 사용 권장
3. **규모 확장**: 상업적 서비스에서는 합법적 데이터 소스가 중요

## 🌟 다음 단계

현재 프로젝트는 다음 데이터 소스로 전환했습니다:

✅ **MovieLens ML-32M** (공개 데이터셋)
- 법적 리스크 없음
- 대규모 평점 데이터
- 협업 필터링 모델 학습에 적합

⏳ **OMDb API** (향후 통합 예정)
- 영화 메타데이터 보강
- 공식 API 사용으로 안정적

자세한 내용은 프로젝트 메인 README를 참조하세요.
