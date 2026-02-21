.PHONY: install dev run test lint docker-up docker-down clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	python -m src.main

test:
	pytest tests/unit/ -v

test-all:
	pytest --cov=src --cov-report=html -v

test-eval:
	pytest tests/evaluation/ -v -m evaluation

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

ingest-sample:
	python -m scripts.ingest_sample --ticker AAPL --filing-type 10-K

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov chroma_db
	find . -type d -name __pycache__ -exec rm -rf {} +
