.PHONY: help install install-dev test lint format clean build docs

help:
	@echo "Available commands:"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code with black and isort"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make build         - Build package"
	@echo "  make docs          - Build documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install -r requirements-dev.txt

test:
	pytest

test-cov:
	pytest --cov=nl2pyflow --cov-report=html --cov-report=term

lint:
	flake8 nl2pyflow tests
	mypy nl2pyflow

format:
	black nl2pyflow tests
	isort nl2pyflow tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

docs:
	cd docs && make html

pre-commit:
	pre-commit install
	pre-commit run --all-files
