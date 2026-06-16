SSH_HOST ?= myserver
LOCAL_PORT ?= 5432
REMOTE_PORT ?= 5432

# ── DB 터널 ────────────────────────────────────────────────────────────────────

.PHONY: db-tunnel
db-tunnel: ## SSH 터널 열기 (포그라운드, Ctrl+C로 종료)
	ssh -N -L $(LOCAL_PORT):localhost:$(REMOTE_PORT) $(SSH_HOST)

.PHONY: db-tunnel-bg
db-tunnel-bg: ## SSH 터널 백그라운드 실행
	ssh -f -N -L $(LOCAL_PORT):localhost:$(REMOTE_PORT) $(SSH_HOST)
	@echo "Tunnel open: localhost:$(LOCAL_PORT) → $(SSH_HOST):$(REMOTE_PORT)"

.PHONY: db-status
db-status: ## 터널 연결 상태 확인
	@nc -z localhost $(LOCAL_PORT) 2>/dev/null \
		&& echo "✓ localhost:$(LOCAL_PORT) connected" \
		|| echo "✗ localhost:$(LOCAL_PORT) not reachable"

.PHONY: db-kill
db-kill: ## 백그라운드 터널 종료
	@pkill -f "ssh -f -N -L $(LOCAL_PORT)" 2>/dev/null \
		&& echo "Tunnel closed" \
		|| echo "No background tunnel found"

.PHONY: db-connect
db-connect: ## psql 직접 접속 (터널이 열려 있어야 함)
	PGPASSWORD=$$(grep POSTGRES_PASSWORD .env 2>/dev/null | cut -d= -f2 | tr -d ' ') \
	psql -h localhost -p $(LOCAL_PORT) \
	     -U $$(grep POSTGRES_USER .env 2>/dev/null | cut -d= -f2 | tr -d ' ') \
	     -d $$(grep POSTGRES_DB .env 2>/dev/null | cut -d= -f2 | tr -d ' ')

# ── 로컬 개발 ──────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Docker 서비스 전체 시작
	docker compose up -d

.PHONY: down
down: ## Docker 서비스 종료
	docker compose down

.PHONY: logs
logs: ## 앱 로그 실시간 확인
	docker compose logs -f app

.PHONY: jupyter
jupyter: ## Jupyter Lab 실행 (notebooks 디렉토리 기준)
	uv run jupyter lab notebooks/

# ── 헬프 ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## 이 도움말 출력
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
