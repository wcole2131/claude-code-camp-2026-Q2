test:
	uv run pytest -v

lint:
	uv run isort --check-only boukensha examples tests
	uv run ruff check boukensha examples tests
	uv run ty check

.PHONY: test lint
