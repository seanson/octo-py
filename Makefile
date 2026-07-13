.PHONY: help install install-dev test test-cov test-watch lint format clean

# Default target
.DEFAULT_GOAL := help

# Help target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation targets
install: ## Install production dependencies
	uv sync --no-dev

install-dev: ## Install all dependencies including dev dependencies
	uv sync

# Testing targets
test: ## Run all tests
	uv run pytest -v

test-cov: ## Run tests with coverage report
	uv run pytest -v --cov=src --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode (requires pytest-watch)
	uv run ptw

test-unit: ## Run only unit tests
	uv run pytest -v tests/test_octopus.py

test-specific: ## Run specific test (use TEST=TestClassName or TEST=test_function_name)
	uv run pytest -v -k "$(TEST)"

# Code quality targets
lint: ## Run linting checks with ruff
	uv run ruff check src tests

format: ## Format code with ruff
	uv run ruff format src tests

format-check: ## Check code formatting without making changes
	uv run ruff format --check src tests

lint-fix: ## Auto-fix linting issues with ruff
	uv run ruff check --fix src tests

# Cleaning targets
clean: ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

# Development targets
dev-setup: install-dev ## Complete development environment setup
	@echo "Development environment ready!"

check: format-check lint test ## Run all checks (format, lint, test)