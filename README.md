# 볼거 없나?

영화/시리즈를 추천하는 서비스를 개발하고 있습니다.
학습용으로 Watcha Pedia에서 데이터를 수집해서 사용하고 있습니다.

## 프로젝트 구조

데이터를 긁어와서 (data scraping) -> 모델링 (modeling) -> 배포 (app, streamlit)

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

- 데이터는 꾸준히 긁어오고 있습니다. (고객-영화 평가 데이터 경우 110만건 이상)
- interaction에 기반한 모델링 MF, item-based filtering 등을 구현해서 streamlit으로 배포했습니다.