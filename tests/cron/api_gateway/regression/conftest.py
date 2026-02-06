"""API Gateway regression test baseline configuration."""

import json
from pathlib import Path

# Baseline API endpoints from test_api.py
API_ENDPOINTS = {
    "health": {
        "method": "GET",
        "path": "/health",
        "auth_required": False,
        "expected_status": 200
    },
    "metrics": {
        "method": "GET",
        "path": "/api/v1/metrics",
        "auth_required": False,
        "expected_status": 200
    },
    "bulk_upsert": {
        "method": "POST",
        "path": "/api/v1/team-members/skill-availability/bulk-upsert",
        "auth_required": True,
        "expected_status": [200, 202]
    },
    "jd_skill_mapping": {
        "method": "POST",
        "path": "/api/v1/jd-skill-mapping/",
        "auth_required": True,
        "expected_status": [200, 202]
    },
    "get_matches": {
        "method": "GET",
        "path": "/api/v1/jd-skill-mapping/{correlation_id}/matches",
        "auth_required": True,
        "expected_status": [200, 404]
    }
}

BASE_URL = "http://localhost:8001"


def save_baseline(responses: dict, filepath: str = "baseline_responses.json"):
    """Save baseline API responses."""
    baseline_path = Path(__file__).parent / filepath
    with open(baseline_path, 'w') as f:
        json.dump(responses, f, indent=2)


def load_baseline(filepath: str = "baseline_responses.json") -> dict:
    """Load baseline API responses."""
    baseline_path = Path(__file__).parent / filepath
    if baseline_path.exists():
        with open(baseline_path, 'r') as f:
            return json.load(f)
    return {}
