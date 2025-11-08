# Argentum Development Makefile

.PHONY: help install test lint format clean bump-patch bump-minor bump-major release

# Default target
help:
	@echo "Argentum Development Commands"
	@echo "============================="
	@echo ""
	@echo "Setup & Development:"
	@echo "  make install     Install package and dependencies"
	@echo "  make test        Run test suite with coverage"
	@echo "  make lint        Run linting and type checking"
	@echo "  make format      Format code with black and isort"
	@echo "  make clean       Clean build artifacts"
	@echo ""
	@echo "Version Management:"
	@echo "  make bump-patch  Bump patch version (0.1.0 -> 0.1.1)"
	@echo "  make bump-minor  Bump minor version (0.1.0 -> 0.2.0)"
	@echo "  make bump-major  Bump major version (0.1.0 -> 1.0.0)"
	@echo "  make release     Create and publish release"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make check       Run tests, linting, and formatting checks"
	@echo "  make all         Install, test, lint, and format"

# Installation
install:
	pip install -e .[dev]
	pre-commit install

install-prod:
	pip install -e .

# Testing
test:
	pytest --cov=argentum --cov-report=term-missing --cov-report=html

test-quick:
	pytest -x --ff

# Code quality
lint:
	flake8 argentum tests
	mypy argentum
	bandit -r argentum

format:
	black argentum tests examples scripts
	isort argentum tests examples scripts

format-check:
	black --check argentum tests examples scripts
	isort --check argentum tests examples scripts

# Security
security-scan:
	bandit -r argentum
	safety check
	pip-audit

# Version bumping (using the smart version manager)
bump-patch:
	@echo "🔄 Bumping patch version..."
	python scripts/version_manager.py patch

bump-minor:
	@echo "🔄 Bumping minor version..."
	python scripts/version_manager.py minor

bump-major:
	@echo "🔄 Bumping major version..."
	python scripts/version_manager.py major

# Quick version bump without tests (for hotfixes)
bump-patch-quick:
	python scripts/version_manager.py patch --no-tests

# Manual bump using bump2version (alternative)
bump2-patch:
	bump2version patch

bump2-minor:
	bump2version minor

bump2-major:
	bump2version major

# Release workflow
release: test lint format-check security-scan
	@echo "🚀 All checks passed! Ready for release."
	@echo "Run 'make bump-minor' or 'make bump-patch' to create release"

# Build and packaging
build:
	python -m build

build-clean: clean build

# Publishing (be careful!)
publish-test:
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish:
	python -m twine upload dist/*

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Development workflow shortcuts
check: test lint format-check security-scan

all: install test lint format

# Git shortcuts
git-status:
	git status --short

git-push:
	git push origin main --tags

# Documentation
docs-build:
	cd docs && make html

docs-serve:
	cd docs && python -m http.server 8000

# Development server for dashboard (if implemented)
dev-server:
	python -m argentum.dev_server

# Export requirements
requirements:
	pip-compile pyproject.toml --output-file requirements.txt
	pip-compile pyproject.toml --extra dev --output-file requirements-dev.txt