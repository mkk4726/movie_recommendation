# UV 사용 가이드

이 프로젝트는 **uv**를 사용하여 의존성을 관리합니다. uv는 Rust로 작성된 매우 빠른 Python 패키지 및 프로젝트 관리 도구입니다.

## 설치

uv가 아직 설치되어 있지 않다면:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Homebrew
brew install uv
```

## 주요 명령어

### 1. 가상 환경 및 의존성 설치

```bash
# pyproject.toml의 의존성을 설치하고 가상 환경 생성
uv sync

# 개발 의존성 포함 설치
uv sync --all-extras
```

### 2. 패키지 추가/제거

```bash
# 새 패키지 설치
uv add <package-name>

# 개발 의존성으로 설치
uv add --dev <package-name>

# 패키지 제거
uv remove <package-name>
```

### 3. Python 실행

```bash
# uv 가상 환경에서 Python 스크립트 실행
uv run python script.py

# Streamlit 앱 실행
uv run streamlit run app.py

# FastAPI 서버 실행
uv run uvicorn app.main:app --reload
```

### 4. Jupyter Notebook

```bash
# Jupyter 커널 생성
uv run python -m ipykernel install --user --name=movie-recommendation

# Jupyter Lab 실행
uv run jupyter lab
```

### 5. 의존성 업데이트

```bash
# 모든 의존성 업데이트
uv lock --upgrade

# 특정 패키지만 업데이트
uv lock --upgrade-package <package-name>
```

### 6. Python 버전 관리

```bash
# Python 버전 확인
uv python list

# 특정 Python 버전으로 동기화
uv sync --python 3.12
```

## Poetry에서 마이그레이션

이 프로젝트는 Poetry에서 uv로 마이그레이션되었습니다:

- ✅ `pyproject.toml`을 PEP 621 표준 형식으로 변환
- ✅ `poetry.lock` → `uv.lock`
- ✅ Poetry 제거 완료

## 주요 차이점

| 기능 | Poetry | uv |
|------|--------|-----|
| 설치 속도 | 보통 | 매우 빠름 (10-100배) |
| 의존성 해결 | 보통 | 매우 빠름 |
| 가상 환경 생성 | `poetry install` | `uv sync` |
| 스크립트 실행 | `poetry run` | `uv run` |
| 패키지 추가 | `poetry add` | `uv add` |

## uv의 장점

1. **속도**: Rust로 작성되어 Poetry보다 훨씬 빠름
2. **표준 준수**: PEP 621 표준을 따름
3. **간단한 설정**: 복잡한 설정 없이 바로 사용 가능
4. **Jupyter 지원**: 가상 환경을 Jupyter 커널로 쉽게 등록 가능

## 문제 해결

### 의존성 설치 실패

```bash
# 캐시 삭제 후 재시도
rm -rf .venv
uv cache clean
uv sync
```

### Python 버전 호환성

이 프로젝트는 Python 3.10-3.12를 지원합니다. Python 3.13은 일부 패키지 호환성 문제로 인해 지원하지 않습니다.

```bash
# Python 3.12 사용
uv sync --python 3.12
```

## 더 알아보기

- [uv 공식 문서](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
