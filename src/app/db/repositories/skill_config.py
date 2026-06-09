"""Skill config repository — loads keyword lists from the skill_config DB table.

Call `load_skill_config(db)` once at application startup (lifespan/startup event).
Afterwards, `get_skill_groups()` and `get_family_keywords()` return the in-memory
cache without hitting the DB again.
"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.models.models import SkillConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback — identical to former settings.py defaults.
# Only used when the DB is unreachable or the table is empty.
# ---------------------------------------------------------------------------
_FALLBACK_GROUPS: Dict[str, List[str]] = {
    "python":     ["python","django","flask","fastapi","pandas","numpy","scikit-learn","pytorch","tensorflow"],
    "javascript": ["javascript","js","typescript","ts","react","node","next.js","angular","vue","html","css"],
    "sql":        ["sql","postgresql","postgres","mysql","sql server","snowflake","oracle","db2"],
    "big_data":   ["spark","pyspark","hadoop","kafka","databricks"],
    "ai_ml":      ["machine learning","ai","ml","nlp","llm","genai","deep learning","computer vision"],
    "cloud":      ["aws","azure","gcp","docker","kubernetes","terraform"],
}

_FALLBACK_FAMILY: Dict[str, List[str]] = {
    "frontend":   ["react","angular","vue","html","css","javascript","js","frontend","ui","ux"],
    "backend":    ["python","java","scala","sql","node","backend","api","spark","snowflake","kafka","ai","ml"],
    "backend_ai": ["backend","ai","ml","data","python","spark","sql","snowflake"],
}

_cache: Dict[str, Dict[str, List[str]]] = {}  # {"group": {...}, "family": {...}}


def load_skill_config(db: Session) -> None:
    """Load all rows from skill_config into the in-memory cache."""
    try:
        rows = db.query(SkillConfig).all()
        groups: Dict[str, List[str]] = {}
        family: Dict[str, List[str]] = {}
        for row in rows:
            if row.config_type == "group":
                groups[row.config_key] = row.keywords
            elif row.config_type == "family":
                family[row.config_key] = row.keywords
        _cache["group"] = groups or _FALLBACK_GROUPS
        _cache["family"] = family or _FALLBACK_FAMILY
        logger.info(
            "skill_config loaded from DB",
            extra={"groups": list(groups), "family_keys": list(family)},
        )
    except Exception:
        logger.warning("Failed to load skill_config from DB — using hardcoded fallback", exc_info=True)
        _cache["group"] = _FALLBACK_GROUPS
        _cache["family"] = _FALLBACK_FAMILY


def get_skill_groups() -> Dict[str, List[str]]:
    return _cache.get("group") or _FALLBACK_GROUPS


def get_family_keywords() -> Dict[str, List[str]]:
    return _cache.get("family") or _FALLBACK_FAMILY
