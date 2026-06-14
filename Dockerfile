FROM python:3.12-slim

WORKDIR /app

# scikit-surprise 빌드에 필요한 컴파일러 + healthcheck용 curl
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (공식 이미지에서 바이너리만 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 파일만 먼저 복사 (레이어 캐시 활용)
COPY pyproject.toml uv.lock ./

# /opt/venv에 venv 생성 — ./src 볼륨 마운트에 덮이지 않도록
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# 프로젝트 자체는 설치하지 않음 (소스는 볼륨에서 마운트)
RUN uv sync --frozen --no-dev --no-install-project

# 소스 코드는 compose.yaml의 볼륨 마운트로 /app/src에 들어옴
ENV PYTHONPATH=/app/src:/app/src/app

EXPOSE 8501

CMD ["/opt/venv/bin/uvicorn", "app.api.main:app", \
     "--host", "0.0.0.0", "--port", "8501"]
