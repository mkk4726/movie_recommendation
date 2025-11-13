# 볼거 없나?

영화 추천 서비스를 개발하고 운영하고 있습니다.
- [영화 추천 서비스 링크](https://movie.mingyuprojects.dev/)

넷플릭스와 같은 OTT에서 뛰어난 추천 모델들을 사용하고 있지만, 막상 사용하다보면 "볼거 없나?"라는 의문과 함께 유튜브나 네이버 등을 통해 검색을 하곤 합니다.
저뿐만 아니라 주변 지인들도 비슷한 경험을 했고, 이는 유튜브에 "넷플릭스 영화 추천"과 같은 동영상이 높은 조회수를 기록한 것을 통해 확인할 수 있습니다.
이를 해결하기 위해 어떤 추천 서비스가 필요할지 고민하고 구현하고 있습니다.

## 📚 프로젝트 진행상황

프로젝트의 상세한 진행상황, 의사결정 과정, 개발 일지는 [`docs/`](docs/) 폴더를 참고해주세요.

- **개발 일지**: [`docs/JOURNAL.md`](docs/JOURNAL.md) - 날짜별 작업 내용과 배운 점
- **의사결정 기록**: [`docs/decisions/`](docs/decisions/) - 주요 기술적 결정 사항들
- **문서 가이드**: [`docs/README.md`](docs/README.md) - 문서화 구조 및 작성 가이드


---

# 데이터셋

ML-32M (MovieLens 32M)데이터셋을 사용합니다.
이 데이터셋에 TMDB API를 통해 메타 데이터를 추가해 사용하고 있습니다.

## 📊 전체 데이터 플로우

```
(MovieLens)          (TMDB API)
      │                   │
      │                   │
      ▼                   ▼
유저-영화 평점 데이터      영화 메타데이터
(user interactions)      (content metadata)
      │                   │
      │                   │
      └─────────┬─────────┘
                ▼
         [조인 / 매핑]
                ▼
    풍부한 영화 데이터셋 생성
    (Interaction + Metadata)
                ▼
    추천 모델 / 데이터 분석 / 시각화
```

---

# 프로젝트 구조

1. 데이터 수집: ML-32M 데이터셋을 data_scraping 모듈에서 로딩 및 가공
2. 모델링: modeling 모듈에서 추천 모델을 개발하고 학습
3. 서비스 배포: app(FastAPI) 모듈로 웹 서비스 운영

```
movie_recommendation/
├── app/                    # FastAPI 웹 애플리케이션
│   ├── api/               # FastAPI 애플리케이션
│   │   ├── main.py        # FastAPI 메인 애플리케이션
│   │   ├── models.py      # 데이터 모델
│   │   ├── app_state.py   # 애플리케이션 상태 관리
│   │   ├── utils.py       # 유틸리티 함수
│   │   └── routes/        # API 라우트
│   │       ├── auth.py    # 인증 라우트
│   │       ├── health.py  # 헬스 체크
│   │       ├── home.py    # 홈 라우트
│   │       ├── movies.py  # 영화 관련 라우트
│   │       ├── ratings.py # 평점 관련 라우트
│   │       └── users.py   # 사용자 관련 라우트
│   ├── main.py            # 실행 진입점
│   ├── modules/           # 애플리케이션 모듈
│   │   ├── config/        # 설정 관리
│   │   ├── core/          # 경로 관리
│   │   ├── data/          # 데이터 처리
│   │   ├── services/      # 비즈니스 로직 서비스
│   │   │   ├── data_access.py
│   │   │   └── recommender_service.py
│   │   └── ui/            # UI 관련 모듈
│   ├── static/            # 정적 파일 (CSS)
│   ├── templates/         # Jinja2 템플릿 (HTML)
│   │   ├── pages/         # 페이지 템플릿
│   │   └── partials/      # 부분 템플릿
│   ├── legacy/            # 레거시 Streamlit 앱
│   │   └── streamlit/     # Streamlit 관련 파일들
│   ├── config.yaml        # 애플리케이션 설정
│   └── README.md          # 앱 문서
├── data_scraping/          # 데이터 스크래핑 및 로딩 모듈
│   ├── common/            # 공통 유틸리티
│   │   ├── data_loader.py      # 데이터 로더
│   │   ├── ml_data_loader.py   # MovieLens 데이터 로더
│   │   ├── tmdb_loader.py      # TMDB API 로더
│   │   ├── omdb_loader.py      # OMDB API 로더
│   │   └── logger.py           # 로깅 유틸리티
│   ├── data/              # 수집된 데이터
│   │   ├── ml-32m/        # MovieLens 32M 데이터셋
│   │   └── tmdb/          # TMDB 메타데이터
│   ├── legacy/            # 레거시 크롤링 코드
│   │   ├── scrapers/      # 스크래퍼 클래스
│   │   └── assets/        # 스크래핑 관련 자산
│   └── README.md          # 스크래핑 상세 문서
├── modeling/               # 모델링 및 분석
│   ├── models/            # 추천 모델 구현
│   │   ├── svd/           # SVD 모델
│   │   ├── item_based/    # 아이템 기반 협업 필터링
│   │   ├── recommender/   # 추천 시스템
│   │   └── query_search/  # 쿼리 검색 모델
│   ├── notebooks/         # Jupyter 노트북
│   ├── utils/             # 모델링 유틸리티
│   └── README.md          # 모델링 문서
├── cold_start/            # 콜드 스타트 처리
│   └── show_random_movies.py
├── user_system/            # Firebase 사용자 인증 시스템
│   ├── firebase_app.py    # Firebase 앱 초기화
│   ├── firebase_auth.py   # 인증 관련
│   ├── firebase_config.py # Firebase 설정
│   ├── firebase_firestore.py # Firestore 관련
│   ├── firebase_recommender.py # Firebase 기반 추천
│   └── README.md
├── pyproject.toml         # Poetry 의존성 관리
├── poetry.lock            # Poetry 의존성 잠금 파일
├── requirements.txt       # pip 의존성
└── README.md             # 메인 문서
```

---

# 제공하는 기능들

제가 운영하고 있는 서비스에서 제공하는 기능들과 어떤 고민을 했는지에 대해 정리했습니다.


## 검색 기능

자연어로 보고 싶은 영화를 검색할 수 있도록 구현했습니다.

### 구현한 내용, 고민 중인 것
가장 기본적으로 BM25를 통해 영화 검색.
필드별로 가중치를 설정해서 사용 ([config.yaml](modeling/models/config.yaml) 참고)

```yaml
field_weights:
  title: 3.0          # 제목에 가장 높은 가중치
  genres: 2.0         # 장르에 중간 가중치
  # tags: 1.0           # 태그에 기본 가중치
  overview: 1.5       # 줄거리/개요에 중간 가중치
``` 

좋은 검색 파이프라인은 뭔지에 대해서 고민하고 있고, 이를 정량적으로 판단하기 위해서 데이터셋을 생성하는 시도를 하고 있습니다.
자세한 내용은 [dataset_generation](dataset_generation/) 디렉토리를 참고해주세요.



## 유사한 영화 추천

영화를 재밌게 본 후에 이와 비슷한 영화가 뭐가 있을지 검색하고 싶을 떄가 있습니다.
이때 사용할 수 있는 기능입니다.

현 시점(25.11.05)에서는 유저의 평점/상호작용 데이터를 바탕으로 한 아이템 기반 협업 필터링(item-based collaborative filtering) 방식의 유사 영화 추천이 제공됩니다.

## 사용자 기반 추천

user_id, item_id가 주어졌을 때 예측평점을 구하는 모델을 통해 평점을 예측하고 높은 영화를 추천하는 구조입니다.

### 구현되어있는 모델
- svd


---

# 📜 Legacy: 과거 시도들

현재 서비스에서 사용하지 않지만 과거에 했던 시도들을 정리해두었습니다.

## 🎬 왓챠피디아 크롤링 

**시도 내용**:
- 왓챠피디아에서 영화 정보, 코멘트, 평점 데이터를 크롤링하여 수집
- Selenium 기반 브라우저 자동화로 110만건 이상의 고객-영화 평가 데이터 수집 성공
- 한국어 영화 리뷰/평점 데이터로 콘텐츠 기반 추천 모델 구축 시도

**중단 사유**:
- 🚨 **법적 위험**: 웹 크롤링 시 이용약관 위반 및 저작권 문제 우려
- ⚖️ **상업적 사용 제한**: 스크래핑 데이터를 상업적으로 활용하기 어려움 (학습용으로 사용하더라도 배포하는 과정에서 위험 요소가 있다고 보임)
- 🔒 **서비스 안정성**: 데이터 소스 플랫폼의 정책 변경에 취약

**전환 결정**:
- 공개 데이터셋인 **MovieLens ML-32M**으로 전환 (법적 리스크 제로)
- 크롤링 코드는 `data_scraping/legacy/` 디렉토리로 이동 보관 (참고용)
- TMDB API 같은 공식 API 활용으로 메타데이터 보강 방향 전환

**교훈**:
- 프로젝트 초기에는 빠른 프로토타이핑이 가능했지만, 스케일링 시 법적 이슈가 장벽
- 추천 시스템 구축에는 안정적이고 합법적인 데이터 소스가 필수
- 상업화를 고려한다면 처음부터 라이선스 정책을 면밀히 검토해야 함