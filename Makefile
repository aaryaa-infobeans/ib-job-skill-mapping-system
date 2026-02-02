.PHONY: install format lint test run clean

install:
	python -m pip install -e ".[dev]"

format:
	black .

lint:
	ruff check .

test:
	pytest -q

run:
	uvicorn app.main:app --app-dir src --reload

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
