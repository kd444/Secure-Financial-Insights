.PHONY: install dev run-backend run-frontend run test lint docker-up docker-down clean

# === Backend ===
install:
	cd backend && pip install -e .

dev:
	cd backend && pip install -e ".[dev]"

run-backend:
	cd backend && python -m src.main

# === Frontend ===
run-frontend:
	cd frontend && pnpm dev

# === Both ===
run:
	@echo "Starting backend and frontend..."
	cd backend && python -m src.main &
	cd frontend && pnpm dev

# === Testing ===
test:
	cd backend && pytest tests/unit/ -v

test-all:
	cd backend && pytest --cov=src --cov-report=html -v

# === Docker ===
docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

# === Clean ===
clean:
	find backend/ -type d -name __pycache__ -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov
	rm -rf frontend/.next frontend/node_modules
