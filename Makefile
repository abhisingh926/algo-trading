.PHONY: help up down logs ps build backend-install backend-dev frontend-install frontend-dev migrate migration test lint format check worker

PY := backend/.venv/bin

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- Docker -----------------------------------------------------------------------------------
up: ## Start the full stack (mysql, redis, backend, frontend)
	docker compose up -d --build

down: ## Stop the stack (keeps the MySQL volume)
	docker compose down

logs: ## Tail backend logs
	docker compose logs -f backend

ps: ## Show container status
	docker compose ps

build: ## Build images
	docker compose build

# ---- Backend ----------------------------------------------------------------------------------
backend-install: ## Create the virtualenv and install backend dependencies
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

backend-dev: ## Run the API with auto-reload (needs mysql: `docker compose up -d mysql redis`)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

worker: ## Run workers as a separate process (set RUN_WORKERS=false for the API)
	cd backend && .venv/bin/python -m app.workers.runner

migrate: ## Apply database migrations
	cd backend && .venv/bin/alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add column"
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

test: ## Run backend tests (in-memory SQLite, mocked brokers - no network)
	cd backend && .venv/bin/pytest -q

lint: ## Ruff + black check
	cd backend && .venv/bin/ruff check app tests && .venv/bin/black --check app tests

format: ## Auto-format backend code
	cd backend && .venv/bin/ruff check --fix app tests && .venv/bin/black app tests

# ---- Frontend ---------------------------------------------------------------------------------
frontend-install: ## Install frontend dependencies
	cd frontend && npm ci

frontend-dev: ## Run the Next.js dev server
	cd frontend && npm run dev

check: lint test ## Everything CI would run
	cd frontend && npm run lint && npx tsc --noEmit
