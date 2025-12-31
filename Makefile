.PHONY: help install test clean run seed-db setup-db docker-up docker-down docker-logs docker-restart docker-build docker-clean docker-ps docker-exec docker-seed docker-token

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install       - Install all dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run all tests with coverage and summary"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make run            - Run the FastAPI server"
	@echo "  make seed-db        - Seed the database with sample data"
	@echo "  make setup-db       - Initialize database tables"
	@echo ""
	@echo "🐳 Docker Compose:"
	@echo "  make docker-up      - Start all services (database, server, Prometheus, Grafana)"
	@echo "  make docker-down    - Stop all services"
	@echo "  make docker-logs    - View app container logs"
	@echo "  make docker-restart - Restart all services"
	@echo "  make docker-rebuild - Rebuild Docker image (use after code changes)"
	@echo "  make docker-build   - Rebuild Docker images"
	@echo "  make docker-clean   - Stop and remove all containers/volumes"
	@echo "  make docker-ps      - Show container status"
	@echo "  make docker-exec    - Open shell in app container"
	@echo "  make docker-seed    - Run database seed script in container"
	@echo "  make docker-token   - Generate admin JWT token in container"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean          - Clean generated files (pyc, cache, coverage)"

# Install dependencies
install:
	pip install -r requirements.txt

# Run all tests with coverage and summary
test:
	@echo "🧪 Running tests with coverage (70% per-file threshold for core logic)..."
	@echo "   Checking: services/ (excluding orchestrator.py, claude_client.py), auth/, database (connection/queries), mcp/tools.py, api/routes/"
	@echo "   Excluded: observability/, config/, schemas/, models.py, utils/, __init__.py, main.py, server.py, seed.py, orchestrator.py, claude_client.py"
	@echo ""
	@if python3 -c "import pytest_cov" 2>/dev/null || python -c "import pytest_cov" 2>/dev/null; then \
		pytest --cov=src --cov-config=.coveragerc --cov-report=term-missing --cov-report=term --cov-fail-under=0 -v --tb=short 2>&1 | tee /tmp/test_output.txt; \
		TEST_EXIT=$$?; \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "🔍 Checking per-file coverage (70% threshold for core logic files)..."; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		if python3 scripts/check_coverage.py /tmp/test_output.txt; then \
			COVERAGE_CHECK=0; \
		else \
			COVERAGE_CHECK=1; \
		fi; \
	else \
		echo "⚠️  pytest-cov not installed, running tests without coverage..."; \
		pytest -v --tb=short 2>&1 | tee /tmp/test_output.txt; \
		TEST_EXIT=$$?; \
		COVERAGE_CHECK=0; \
	fi; \
	echo ""; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "📊 Test Summary:"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	PASSED=$$(grep -E "passed|PASSED" /tmp/test_output.txt | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1 || echo "0"); \
	FAILED=$$(grep -E "failed|FAILED" /tmp/test_output.txt | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" | head -1 || echo "0"); \
	ERROR=$$(grep -E "error|ERROR" /tmp/test_output.txt | grep -oE "[0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0"); \
	PASSED=$${PASSED:-0}; \
	FAILED=$${FAILED:-0}; \
	ERROR=$${ERROR:-0}; \
	TOTAL=$$((PASSED + FAILED + ERROR)); \
	echo "  ✅ Passed: $$PASSED"; \
	echo "  ❌ Failed: $$FAILED"; \
	echo "  ⚠️  Errors: $$ERROR"; \
	echo "  📈 Total:  $$TOTAL"; \
	echo ""; \
	if python3 -c "import pytest_cov" 2>/dev/null || python -c "import pytest_cov" 2>/dev/null; then \
		COVERAGE=$$(grep -E "^TOTAL|^src" /tmp/test_output.txt | tail -1 | grep -oE "[0-9]+%" | head -1 || echo "N/A"); \
		echo "📈 Total Code Coverage: $$COVERAGE"; \
	else \
		echo "📈 Code Coverage: N/A (pytest-cov not installed)"; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo ""; \
	rm -f /tmp/test_output.txt; \
	if [ $$TEST_EXIT -ne 0 ]; then exit $$TEST_EXIT; fi; \
	if [ $$COVERAGE_CHECK -ne 0 ]; then exit $$COVERAGE_CHECK; fi; \
	exit 0

# Run the FastAPI server
run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Seed database with sample data
seed-db:
	python -m src.database.seed

# Setup database (create tables)
setup-db:
	python -c "from src.database.connection import database, Base; from src.config.settings import settings; from src.database import models; database.initialize(settings.DATABASE_URL); database.create_tables(); print('✅ Database tables created')"

# Docker Compose commands
docker-up:
	@echo "🚀 Starting all services with Docker Compose..."
	@if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "financial-mcp-server\|cortx.*app"; then \
		echo "📦 App image not found, building first..." ; \
		docker-compose build app ; \
	fi
	docker-compose up -d
	@echo ""
	@echo "✅ Services started! View logs with: make docker-logs"
	@echo "   Access:"
	@echo "   - API: http://localhost:8000"
	@echo "   - Prometheus: http://localhost:9090"
	@echo "   - Grafana: http://localhost:3000"

docker-down:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ Services stopped"

docker-logs:
	@echo "📋 Viewing logs (Ctrl+C to exit)..."
	docker-compose logs -f app

docker-restart:
	@echo "🔄 Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted"

docker-rebuild:
	@echo "🔨 Rebuilding Docker images..."
	docker-compose build app
	@echo "✅ Image rebuilt. Use 'make docker-up' to start with new image"

docker-build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Build complete"

docker-clean:
	@echo "🧹 Stopping and removing containers, networks, volumes, and images..."
	docker-compose down -v --rmi local
	@echo "✅ Cleanup complete (containers, volumes, networks, and images removed)"

docker-ps:
	@echo "📊 Container status:"
	docker-compose ps

docker-exec:
	@echo "💻 Opening shell in app container..."
	docker-compose exec app /bin/sh

docker-seed:
	@echo "🌱 Running database seed script..."
	docker-compose exec app python -m src.database.seed

docker-token:
	@echo "🔑 Generating admin JWT token..."
	docker-compose exec app python scripts/generate_admin_token.py

# Clean generated files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	@echo "✅ Cleaned generated files"
