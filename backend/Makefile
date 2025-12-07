# =============================================================================
# B&R Capital Dashboard Backend - Makefile
# =============================================================================
# Convenience commands for development, testing, and deployment
# Usage: make <target>
# =============================================================================

.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate seed

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# =============================================================================
# Help
# =============================================================================
help:
	@echo "$(BLUE)B&R Capital Dashboard Backend$(RESET)"
	@echo "$(YELLOW)Available commands:$(RESET)"
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Start development server"
	@echo "  make shell        - Start Python shell with app context"
	@echo ""
	@echo "$(GREEN)Testing:$(RESET)"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make test-fast    - Run tests without slow tests"
	@echo ""
	@echo "$(GREEN)Code Quality:$(RESET)"
	@echo "  make lint         - Run linters (flake8, mypy)"
	@echo "  make format       - Format code (black, isort)"
	@echo "  make check        - Run all quality checks"
	@echo ""
	@echo "$(GREEN)Database:$(RESET)"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-new  - Create new migration"
	@echo "  make seed         - Seed database with mock data"
	@echo "  make db-reset     - Reset database (drop & recreate)"
	@echo ""
	@echo "$(GREEN)Docker:$(RESET)"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start all containers"
	@echo "  make docker-down  - Stop all containers"
	@echo "  make docker-logs  - View container logs"
	@echo "  make docker-shell - Shell into backend container"
	@echo ""
	@echo "$(GREEN)Cleanup:$(RESET)"
	@echo "  make clean        - Remove cache files"
	@echo "  make clean-all    - Remove all generated files"

# =============================================================================
# Development
# =============================================================================
install:
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt 2>/dev/null || true
	@echo "$(GREEN)Dependencies installed!$(RESET)"

dev:
	@echo "$(BLUE)Starting development server...$(RESET)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

shell:
	@echo "$(BLUE)Starting Python shell...$(RESET)"
	python -c "from app.main import app; import IPython; IPython.embed()"

# =============================================================================
# Testing
# =============================================================================
test:
	@echo "$(BLUE)Running tests...$(RESET)"
	pytest tests/ -v

test-cov:
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-fast:
	@echo "$(BLUE)Running fast tests...$(RESET)"
	pytest tests/ -v -m "not slow"

# =============================================================================
# Code Quality
# =============================================================================
lint:
	@echo "$(BLUE)Running linters...$(RESET)"
	flake8 app/ tests/ --max-line-length=120 --ignore=E501,W503
	mypy app/ --ignore-missing-imports

format:
	@echo "$(BLUE)Formatting code...$(RESET)"
	black app/ tests/
	isort app/ tests/

check: format lint test
	@echo "$(GREEN)All checks passed!$(RESET)"

# =============================================================================
# Database
# =============================================================================
migrate:
	@echo "$(BLUE)Running database migrations...$(RESET)"
	alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

seed:
	@echo "$(BLUE)Seeding database...$(RESET)"
	python -m app.database.seed

db-reset:
	@echo "$(RED)Resetting database...$(RESET)"
	alembic downgrade base
	alembic upgrade head
	@echo "$(GREEN)Database reset complete!$(RESET)"

# =============================================================================
# Docker
# =============================================================================
docker-build:
	@echo "$(BLUE)Building Docker images...$(RESET)"
	docker-compose build

docker-up:
	@echo "$(BLUE)Starting containers...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)Containers started!$(RESET)"
	@echo "  API: http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"

docker-down:
	@echo "$(BLUE)Stopping containers...$(RESET)"
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec backend /bin/bash

docker-prod:
	@echo "$(BLUE)Starting production containers...$(RESET)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker-clean:
	@echo "$(RED)Removing containers and volumes...$(RESET)"
	docker-compose down -v --remove-orphans

# =============================================================================
# Cleanup
# =============================================================================
clean:
	@echo "$(BLUE)Cleaning cache files...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cache cleaned!$(RESET)"

clean-all: clean
	@echo "$(RED)Removing all generated files...$(RESET)"
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf dist/ build/ *.egg-info
	@echo "$(GREEN)All generated files removed!$(RESET)"
