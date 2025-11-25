# 레거시 Streamlit 앱

⚠️ **이 폴더는 레거시 코드입니다. 더 이상 메인 개발 대상이 아닙니다.**

이전에 사용하던 Streamlit 기반 웹 애플리케이션이 보관되어 있습니다.

## 현재 상태

- **메인 앱**: FastAPI로 전환됨 (`app/api.py`, `app/main.py`)
- **이 폴더**: 참고용으로만 보관
- **Firebase 통합**: 이전에 Streamlit에서 사용하던 Firebase 인증 기능 포함

## 구조

```
legacy/streamlit/
├── app.py              # Streamlit 메인 앱
├── modules/
│   ├── ui/            # Streamlit UI 컴포넌트
│   │   ├── components.py
│   │   ├── sidebar.py
│   │   ├── movie_based.py
│   │   ├── user_based.py
│   │   └── rating_management.py
│   ├── services/      # Streamlit 캐싱이 있는 서비스
│   │   ├── data_service.py
│   │   └── recommender.py
│   ├── data/          # Streamlit 캐싱이 있는 데이터 로더
│   │   └── loader.py
│   └── config/        # Streamlit 캐싱이 있는 설정 로더
│       ├── loader.py
│       └── config.yaml
└── README.md          # 이 파일
```

## 실행 방법 (참고용)

### 사전 준비
1. 학습된 모델 파일 확인
2. 필요한 패키지 설치 (`pip install -r requirements.txt`)
3. Firebase 설정 (선택사항)

### 실행
```bash
cd app/legacy/streamlit
streamlit run app.py
```

## 메인 앱과의 차이점

| 구분 | 레거시 Streamlit | 메인 FastAPI |
|------|----------------|-------------|
| 프레임워크 | Streamlit | FastAPI |
| 실행 방식 | `streamlit run` | `uvicorn` 또는 `python -m app.main` |
| UI | Streamlit 자동 UI | Jinja2 템플릿 + HTML/CSS |
| 캐싱 | `@st.cache_data`, `@st.cache_resource` | `@lru_cache` |
| API | 없음 (웹 앱만) | REST API 제공 |
| Firebase | 통합됨 | 미통합 (향후 추가 예정) |

## 참고 사항

- 이 코드는 작동하지만 더 이상 유지보수되지 않습니다
- 새로운 기능은 FastAPI 앱에 추가됩니다
- Firebase 인증 기능은 필요시 FastAPI 앱으로 이식 가능합니다

