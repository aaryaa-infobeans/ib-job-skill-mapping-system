# IB Job Skill Mapping System

A system for mapping job descriptions to skills and evaluating candidate availability.

## Setup

```bash
python -m pip install -e ".[dev]"
docker compose up -d postgres
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --app-dir src --reload
```

## Test

```bash
black .
ruff check .
pytest -q
```
