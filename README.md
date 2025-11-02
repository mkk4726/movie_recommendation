# 볼거 없나?

영화/시리즈를 추천하는 서비스를 개발하고 있습니다.
**ML-32M (MovieLens 32M)** 데이터셋을 사용합니다.

## 프로젝트 구조

ML-32M Dataset 로딩 (data_scraping) -> 모델링 (modeling) -> 배포 (app, streamlit)

```
movie_recommendation/
├── app/                    # 스트림릿 웹 애플리케이션
│   ├── models/            # 학습된 추천 모델
│   ├── utils/             # 앱 유틸리티 함수
│   ├── streamlit_app.py   # 메인 앱 파일
│   ├── train_and_save_model.py  # 모델 학습 스크립트
│   └── requirements.txt   # 앱 의존성
├── data_scraping/          # 데이터 스크래핑 모듈
│   ├── common/            # 공통 유틸리티
│   ├── scrapers/          # 스크래퍼 클래스
│   ├── data/              # 수집된 데이터
│   ├── debug/             # 디버깅 스크립트
│   ├── legacy/            # 레거시 코드
│   └── README.md          # 스크래핑 상세 문서
├── modeling/               # 모델링 및 분석
│   ├── notebooks/         # Jupyter 노트북
│   ├── utils/             # 모델링 유틸리티
│   └── README.md          # 모델링 문서
├── pyproject.toml         # Poetry 의존성 관리
├── poetry.lock            # Poetry 의존성 잠금 파일
├── requirements.txt       # pip 의존성
└── README.md             # 메인 문서
```

## 진행 상황

### 🗃️ 데이터 현황
- **ML-32M Dataset**: 87,585개 영화, 3,200만개+ 평점 사용 (협업 필터링)
- **Legacy**: 왓챠피디아 크롤링 데이터는 법적 위험으로 인해 `data_scraping/legacy/`로 이동되어 더 이상 사용하지 않음
- **향후 계획**: OMDb API 통합으로 메타데이터 보강 예정

### 🤖 모델링
- Interaction 기반: Matrix Factorization (SVD), Item-based Filtering 구현 완료
- Streamlit 앱 배포: 유저 기반 / 아이템 기반 추천 서비스 운영 중

---

## 🎯 개발 방향: 데이터 파이프라인 아키텍처

현재 프로젝트는 **MovieLens Dataset + OMDb API** 조합으로 영화 추천 시스템을 구축하고 있습니다.

### 📊 전체 데이터 플로우

```
(MovieLens)          (OMDb API)
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

### 🧩 각 데이터 소스의 역할

#### 1️⃣ **MovieLens Dataset** → 사용자 행동 (Interaction) 데이터

- **출처**: [GroupLens Research](https://grouplens.org/datasets/movielens/)
- **위치**: `data_scraping/ml-32m/` (ML-32M 크기 사용)
- **주요 파일**:
  - `ratings.csv`: 유저-영화 평점 (userId, movieId, rating, timestamp)
  - `movies.csv`: 영화 기본 정보 (movieId, title, genres)
  - `tags.csv`: 유저가 작성한 태그
- **활용**: 협업 필터링, Matrix Factorization, Neural CF 등 유저-아이템 매트릭스 학습

#### 2️⃣ **OMDb API** → 영화 콘텐츠 메타데이터

- **목적**: 영화 제목을 기반으로 추가 메타데이터 가져오기
- **데이터**: title, year, director, actors, plot, imdbRating, poster, genre
- **사용법**: MovieLens 영화 제목 → OMDb API 쿼리 → IMDb 데이터 병합

### 🔄 데이터 결합 전략

```python
MovieLens 영화 제목 
    ↓
OMDb API 호출 (영화 제목 기반)
    ↓
추가 메타데이터 수집 (감독, 배우, 포스터, 줄거리 등)
    ↓
MovieLens 평점 데이터와 병합
    ↓
하이브리드 추천 모델 학습 준비 완료
```

### 📈 활용 사례

| 분야 | 활용 방법 |
|------|----------|
| 🎯 **추천 시스템** | 하이브리드 추천 (CF + 콘텐츠 기반) |
| 🧠 **ML Feature Engineering** | 감독/배우/장르 임베딩 피처 생성 |
| 📊 **시각화** | 장르별 평균 평점, 배우별 평점 분포 |
| 🎥 **앱 서비스** | 포스터·설명 포함 UI 제작 |

### ⚠️ 주의사항

- **MovieLens 한계**: 최신 영화 데이터는 2023년 이전까지만 제공
- **OMDb API 제한**: 무료 API는 하루 1,000건 제한 → **샘플링 + 캐싱 필수**
- **라이선스**: 상업적 서비스에서는 OMDb 데이터 직접 재배포 불가

### 🎬 다음 단계

- [ ] OMDb API 통합 스크립트 작성
- [ ] 메타데이터 캐싱 시스템 구축
- [ ] 하이브리드 추천 모델 개발
- [ ] 콘텐츠 기반 피처 엔지니어링
- [ ] 포스터 포함 UI 개선

---

## 📜 Legacy: 과거 시도 사항

프로젝트 초기에는 다양한 데이터 소스와 방법론을 시도했습니다. 참고용으로 기록합니다.

### 🎬 왓챠피디아 크롤링 시도

**시도 내용**:
- 왓챠피디아에서 영화 정보, 코멘트, 평점 데이터를 크롤링하여 수집
- Selenium 기반 브라우저 자동화로 110만건 이상의 고객-영화 평가 데이터 수집 성공
- 한국어 영화 리뷰/평점 데이터로 콘텐츠 기반 추천 모델 구축 시도

**중단 사유**:
- 🚨 **법적 위험**: 웹 크롤링 시 이용약관 위반 및 저작권 문제 우려
- ⚖️ **상업적 사용 제한**: 스크래핑 데이터를 상업적으로 활용하기 어려움
- 🔒 **서비스 안정성**: 데이터 소스 플랫폼의 정책 변경에 취약

**전환 결정**:
- 공개 데이터셋인 **MovieLens ML-32M**으로 전환 (법적 리스크 제로)
- 크롤링 코드는 `data_scraping/legacy/` 디렉토리로 이동 보관 (참고용)
- OMDb API 같은 공식 API 활용으로 메타데이터 보강 방향 전환

**교훈**:
- 프로젝트 초기에는 빠른 프로토타이핑이 가능했지만, 스케일링 시 법적 이슈가 장벽
- 추천 시스템 구축에는 안정적이고 합법적인 데이터 소스가 필수
- 상업화를 고려한다면 처음부터 라이선스 정책을 면밀히 검토해야 함