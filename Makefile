.PHONY: help install up down logs test test-unit test-integration test-contract \
        migrate migrate-create lint format typecheck clean load-test

# ─────────────────────────────────────────────
# Default target — show help
# ─────────────────────────────────────────────
help:
	@echo ""
	@echo "  llm-tagger-api — Developer Commands"
	@echo "  ────────────────────────────────────"
	@echo "  Setup:"
	@echo "    make install        Install all dependencies with uv"
	@echo "    make env            Copy .env.example to .env"
	@echo ""
	@echo "  Docker:"
	@echo "    make up             Start all services"
	@echo "    make down           Stop all services"
	@echo "    make restart        Restart app + worker only"
	@echo "    make logs           Follow logs for all services"
	@echo "    make logs-app       Follow app logs only"
	@echo "    make logs-worker    Follow worker logs only"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate        Run pending migrations"
	@echo "    make migrate-create name=your_migration_name"
	@echo "    make migrate-down   Rollback last migration"
	@echo "    make db-reset       Drop and recreate database"
	@echo ""
	@echo "  Testing:"
	@echo "    make test           Run full test suite"
	@echo "    make test-unit      Run unit tests only (fast)"
	@echo "    make test-int       Run integration tests only"
	@echo "    make test-contract  Run contract tests only"
	@echo "    make test-cov       Run tests with HTML coverage report"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint           Run ruff linter"
	@echo "    make format         Auto-format with ruff"
	@echo "    make typecheck      Run mypy type checker"
	@echo "    make check          Run lint + typecheck together"
	@echo ""
	@echo "  Load Testing:"
	@echo "    make load-test      Run Locust load test (opens browser UI)"
	@echo ""

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────
install:
	uv sync

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ .env created from .env.example — fill in your values"; \
	else \
		echo "⚠ .env already exists — not overwriting"; \
	fi

# ─────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────
up:
	docker compose up -d
	@echo ""
	@echo "  Services running:"
	@echo "  → API:        http://localhost:8000"
	@echo "  → API Docs:   http://localhost:8000/docs"
	@echo "  → Langfuse:   http://localhost:3001"
	@echo "  → Prometheus: http://localhost:9090"
	@echo "  → Grafana:    http://localhost:3002 (admin/admin)"
	@echo ""

down:
	docker compose down

restart:
	docker compose restart app worker

logs:
	docker compose logs -f

logs-app:
	docker compose logs -f app

logs-worker:
	docker compose logs -f worker

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
migrate:
	uv run alembic upgrade head

migrate-create:
	@if [ -z "$(name)" ]; then echo "Usage: make migrate-create name=your_migration"; exit 1; fi
	uv run alembic revision --autogenerate -m "$(name)"

migrate-down:
	uv run alembic downgrade -1

db-reset:
	docker compose stop postgres pgbouncer
	docker compose rm -f postgres pgbouncer
	docker volume rm llm-tagger-api_postgres_data 2>/dev/null || true
	docker compose up -d postgres pgbouncer
	@echo "Waiting for postgres to be ready..."
	@sleep 5
	make migrate

# ─────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v -m unit

test-int:
	uv run pytest tests/integration/ -v -m integration

test-contract:
	uv run pytest tests/contract/ -v -m contract

test-cov:
	uv run pytest tests/ --cov=src/tagging --cov-report=html:coverage-html
	@echo "✓ Coverage report: open coverage-html/index.html"

test-watch:
	uv run pytest-watch tests/unit/ -- -v -m unit

# ─────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────
lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck:
	uv run mypy src/

check: lint typecheck

# ─────────────────────────────────────────────
# Load Testing
# ─────────────────────────────────────────────
load-test:
	uv run locust -f tests/load/locustfile.py --host=http://localhost:8000

# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "coverage-html" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ cleaned"
