.PHONY: install format lint test test-agents demo run clean

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

test-agents:
	PYTHONPATH=src LOG_LEVEL=INFO SECRETS_BACKEND=none DATABASE_URL=sqlite:///tmp/test.db \
	python -m pytest tests/unit/test_agent_framework.py tests/unit/test_config_loader.py \
		tests/unit/test_orchestrator.py tests/unit/test_migration_agents.py \
		tests/unit/test_observability.py tests/unit/test_hot_reload.py \
		tests/unit/test_integration.py --noconftest -v

demo:
	PYTHONPATH=src python scripts/demo_agent_pipeline.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
