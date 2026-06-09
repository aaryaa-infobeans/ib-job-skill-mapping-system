.PHONY: install format lint test run clean db-reset db-dump

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

# Team DB sync targets
# db-dump: run this before committing a data snapshot
db-dump:
	@echo "--- Dumping current DB ---"
	@mkdir -p db
	docker compose exec -T postgres sh -c 'pg_dump -U user -Fc ib_job_skill_mapping' > db/ib_job_skill_mapping_latest.sql
	@echo "--- Dump saved to db/ib_job_skill_mapping_latest.sql (git add + commit it) ---"

# db-reset: teammates run this after git pull to restore your DB state
db-reset:
	@echo "--- Tearing down old DB volume ---"
	docker compose down -v
	docker compose up -d postgres
	@echo "--- Waiting for postgres ---"
	@until docker compose exec -T postgres pg_isready -U user -q; do sleep 2; done
	@echo "--- Restoring data snapshot ---"
	docker compose cp db/ib_job_skill_mapping_latest.sql postgres:/tmp/dump.sql
	docker compose exec -T postgres sh -c 'pg_restore -U user -d ib_job_skill_mapping --clean --if-exists /tmp/dump.sql; echo done'
	@echo "--- Applying migrations ---"
	alembic upgrade head
	@echo "--- DB reset complete ---"
