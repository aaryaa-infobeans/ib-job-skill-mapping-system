# Quick Reference - IB Job Skill Mapping System

## 🚀 Start Development (3 commands)

```bash
cd /var/www/html/ib-job-skill-mapping-system
source venv/bin/activate
python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port 9000
```

**Server runs at**: http://127.0.0.1:9000
**API Docs**: http://127.0.0.1:9000/docs

---

## 📊 Credentials

| Component | Value |
|-----------|-------|
| **Database** | `postgresql://postgres:StrongPostgresPassword!@localhost:5432/ib_requisition_skill_match_v2` |
| **OpenAI Key** | `sk-proj-8TRfh31...` (in .env) |
| **JWT Secret** | `k3DTLLHdL9u0...` (in .env) |
| **OAuth Client** | `INFOBEANS_TA` |

---

## ✅ Verification Checklist

- [x] Python 3.13 virtual environment
- [x] All dependencies installed
- [x] PostgreSQL database created & migrated
- [x] Configuration file (.env) created
- [x] API server running
- [x] Health check passing
- [x] Sample data loaded

---

## 📚 Key Files

| File | Purpose |
|------|---------|
| `.env` | Configuration & secrets |
| `src/app/main.py` | API entry point |
| `src/app/ai/` | LangGraph AI agents |
| `src/app/api/routers/` | API endpoints |
| `tests/` | Test suite |
| `alembic/` | Database migrations |

---

## 🔧 Common Commands

### Development
```bash
# Run with auto-reload
python -m uvicorn src.app.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Format code
black src/

# Lint code
ruff check src/
```

### Database
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "migration_name"

# View migration history
alembic history
```

---

## 📝 Environment Variables (.env)

```
DATABASE_URL=postgresql://postgres:StrongPostgresPassword!@localhost:5432/ib_requisition_skill_match_v2
JWT_SECRET_KEY=k3DTLLHdL9u0hcEErdZ-RMdXaNfTDLami3-O9oVD6tk
LOG_LEVEL=INFO
```

---

## 🌐 API Quick Test

```bash
# Health check
curl http://127.0.0.1:9000/health

# With JSON formatting
curl -s http://127.0.0.1:9000/health | python -m json.tool
```

---

## 📖 Documentation

- **Setup Details**: [SETUP_COMPLETE.md](./SETUP_COMPLETE.md)
- **Full README**: [README.md](./README.md)
- **Architecture**: [docs/architecture/overview.md](./docs/architecture/overview.md)
- **Local Dev Guide**: [docs/runbooks/local_dev.md](./docs/runbooks/local_dev.md)

---

**Ready to develop!** 🎉
