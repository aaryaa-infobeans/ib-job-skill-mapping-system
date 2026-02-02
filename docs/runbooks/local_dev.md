# Local Development Runbook

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL client (optional)

## Setup

1. Clone repository
2. Install dependencies: `python -m pip install -e ".[dev]"`
3. Start database: `docker compose up -d postgres`
4. Run migrations: `alembic upgrade head`
5. Start API: `uvicorn app.main:app --app-dir src --reload`

## Testing

```bash
black .
ruff check .
pytest -q
```
