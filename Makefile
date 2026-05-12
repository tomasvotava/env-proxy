PACKAGE := env_proxy
SOURCES := env_proxy tests benchmarks
POETRY := poetry

.DEFAULT_GOAL := help

.PHONY: help install format format-check lint lint-fix typecheck test bench ci docs-serve docs-build clean

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install runtime + dev + docs dependencies via Poetry.
	$(POETRY) install --with docs

format: ## Auto-format with ruff.
	$(POETRY) run ruff format $(SOURCES)

format-check: ## Verify formatting without writing (CI-equivalent).
	$(POETRY) run ruff format --check $(SOURCES)

lint: ## Lint with ruff.
	$(POETRY) run ruff check $(SOURCES)

lint-fix: ## Lint with ruff and apply safe fixes.
	$(POETRY) run ruff check --fix $(SOURCES)

typecheck: ## Type-check with mypy.
	$(POETRY) run mypy $(SOURCES)

test: ## Run the test suite with coverage.
	$(POETRY) run pytest -vv tests/

bench: ## Run benchmarks (skips coverage).
	$(POETRY) run pytest benchmarks/ --no-cov

ci: format-check lint typecheck test ## Run every check that CI runs (in order).

docs-serve: ## Serve docs locally with live reload at http://127.0.0.1:8000.
	DISABLE_MKDOCS_2_WARNING=true $(POETRY) run mkdocs serve

docs-build: ## Build docs in --strict mode (fails on warnings).
	DISABLE_MKDOCS_2_WARNING=true $(POETRY) run mkdocs build --strict

clean: ## Remove build, cache, and coverage artifacts.
	rm -rf site/ .coverage coverage.xml coverage.json .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
