.PHONY: help build up down restart logs shell test coverage format lint migrate makemigrations update-python update-frontend pre-commit-install clean celery-logs celery-shell

help:
	@echo "FastAPI Basic Template - Available commands:"
	@echo "  make build                 - Build Docker images"
	@echo "  make up                    - Start all services"
	@echo "  make down                  - Stop all services"
	@echo "  make restart               - Restart all services"
	@echo "  make logs                  - View logs"
	@echo "  make shell                 - Open shell in app container"
	@echo "  make test                  - Run tests"
	@echo "  make coverage              - Run tests with coverage report"
	@echo "  make format                - Format code with ruff"
	@echo "  make lint                  - Lint code with ruff"
	@echo "  make migrate               - Run database migrations"
	@echo "  make makemigrations        - Create new migration"
	@echo "  make update-python         - Update Python dependencies"
	@echo "  make update-frontend       - Update frontend dependencies"
	@echo "  make pre-commit-install    - Install pre-commit hooks"
	@echo "  make celery-logs           - View Celery worker logs"
	@echo "  make celery-shell          - Open shell in Celery worker container"
	@echo "  make clean                 - Clean up containers, volumes, and images"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Services started. App available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"
	@echo "Admin panel at http://localhost:8000/admin"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

shell:
	docker compose exec app /bin/bash

test:
	docker compose exec app pytest

coverage:
	docker compose exec app pytest --cov=app --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

format:
	.venv-precommit/bin/ruff format .
	.venv-precommit/bin/ruff check --fix .

lint:
	.venv-precommit/bin/ruff check .

migrate:
	docker compose exec app alembic upgrade head

makemigrations:
	@read -p "Enter migration message: " message; \
	docker compose exec app alembic revision --autogenerate -m "$$message"

update-python:
	docker compose exec app pip install --upgrade pip
	docker compose exec app pip install --upgrade -r docker/app/requirements.txt

update-frontend:
	docker compose exec postcss npm update

pre-commit-install:
	python3.14 -m venv .venv-precommit
	.venv-precommit/bin/pip install -r requirements-precommit.txt
	.venv-precommit/bin/pre-commit install
	@echo "Pre-commit hooks installed"

celery-logs:
	docker compose logs -f celery-worker celery-beat

celery-shell:
	docker compose exec celery-worker /bin/bash

clean:
	docker compose down -v --rmi local --remove-orphans
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
