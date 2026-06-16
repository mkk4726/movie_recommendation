# 원격 DB 접속 가이드 (로컬 모델링용)

서버에서 Docker로 돌고 있는 PostgreSQL에 로컬 Jupyter/Python에서 접근하는 방법입니다.

## 구조

```
Mac (Python/Jupyter)
    │
    └─ localhost:5432
            │  (SSH 터널)
            ▼
    Server SSH Port 22
            │
            └─ localhost:5432 (Docker postgres container)
```

---

## 1. 사전 준비

### SSH Config 설정 (선택, 편의용)

`~/.ssh/config`에 서버 정보를 등록해두면 `make db-tunnel`만으로 접속됩니다.

```
Host movie-server
    HostName <서버 IP 또는 도메인>
    User <서버 유저명>
    IdentityFile ~/.ssh/id_rsa   # 키 파일 경로 (없으면 삭제)
```

### Python 패키지 설치

```bash
uv add psycopg2-binary sqlalchemy pandas
# 또는
pip install psycopg2-binary sqlalchemy pandas
```

---

## 2. SSH 터널 열기

```bash
# Makefile 사용 (권장)
make db-tunnel

# 직접 실행
ssh -N -L 5432:localhost:5432 movie-server
# 또는 SSH Config 없이
ssh -N -L 5432:localhost:5432 유저명@서버IP
```

터미널 하나를 차지합니다. 백그라운드로 실행하려면:

```bash
make db-tunnel-bg
```

---

## 3. 터널 연결 확인

```bash
make db-status
# 또는
nc -z localhost 5432 && echo "connected" || echo "not connected"
```

---

## 4. Python/Jupyter에서 연결

### 기본 연결

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine(
    "postgresql://movie_user:movie_pass@localhost:5432/movie_recommendation"
)
```

### `.env` 파일에서 읽기 (권장)

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}"
    f"/{os.getenv('POSTGRES_DB')}"
)
```

### 데이터 불러오기

```python
# 전체 테이블
df = pd.read_sql("SELECT * FROM ratings LIMIT 1000", engine)

# 쿼리로 필터링
df = pd.read_sql("""
    SELECT user_id, movie_id, rating, created_at
    FROM ratings
    WHERE created_at >= '2025-01-01'
    ORDER BY created_at DESC
""", engine)

print(df.shape)
df.head()
```

---

## 5. 주요 테이블

| 테이블 | 설명 |
|--------|------|
| `ratings` | 유저 평점 로그 |
| `search_logs` | 검색 로그 |
| `click_logs` | 클릭 로그 |

스키마 확인:

```python
import sqlalchemy as sa

inspector = sa.inspect(engine)
print(inspector.get_table_names())

# 컬럼 확인
for col in inspector.get_columns("ratings"):
    print(col["name"], col["type"])
```

---

## 6. 터널 종료

```bash
make db-kill
```

---

## 주의사항

- 로컬 포트 5432가 이미 사용 중이면 터널이 실패합니다. `make db-kill` 후 재시도하거나 다른 포트를 지정하세요.
- `.env` 파일에 실제 비밀번호를 저장하고 git에 올리지 않도록 주의하세요 (`.gitignore`에 이미 포함됨).
