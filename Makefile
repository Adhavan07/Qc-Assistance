.PHONY: help setup dev dev-docker test lint format build migrate seed clean

help:
	@echo "Wiring Diagram QC Assistant - Monorepo Management"
	@echo ""
	@echo "Commands:"
	@echo "  make setup       Install all backend and frontend dependencies"
	@echo "  make dev         Run backend and frontend servers locally"
	@echo "  make dev-docker  Start all services using Docker Compose"
	@echo "  make test        Execute complete Python pytest test suite"
	@echo "  make lint        Run ruff/flake8 and ESLint checks"
	@echo "  make format      Format Python and TypeScript code"
	@echo "  make build       Build Next.js frontend production bundle"
	@echo "  make migrate     Run database migrations via Alembic"
	@echo "  make seed        Seed initial demo tenant, users, and rules"
	@echo "  make clean       Remove temporary build caches and log files"

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	npm run dev

dev-docker:
	docker compose up -d

test:
	.venv/bin/pytest -v

lint:
	cd frontend && npm run lint

build:
	npm run build

migrate:
	.venv/bin/alembic -c backend/alembic.ini upgrade head

seed:
	.venv/bin/python3 -m backend.src.infrastructure.seed

clean:
	rm -rf .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	cd frontend && rm -rf .next out
