"""Configuration for Google Drive MCP server."""

import os
from pathlib import Path

# Repo root = 4 levels above this file (src/mcp_servers/gdrive/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Path to Google Service Account key file (used when OAuth token not present)
SA_KEY_PATH: str = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE", str(_REPO_ROOT / "secrets" / "sa-key.json")
)

# Path to OAuth2 user credentials token file.
# Generated once by scripts/setup_gdrive_oauth.py.
# Takes precedence over SA_KEY_PATH when present.
OAUTH_TOKEN_PATH: str = os.environ.get(
    "GOOGLE_OAUTH_TOKEN_FILE",
    str(_REPO_ROOT / "secrets" / "oauth-token.json"),
)

# Path to OAuth2 client secrets file (downloaded from GCP Console).
OAUTH_CLIENT_SECRETS_PATH: str = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_SECRETS_FILE",
    str(_REPO_ROOT / "secrets" / "oauth-client-secrets.json"),
)

# OAuth scopes
DRIVE_SCOPES: list[str] = ["https://www.googleapis.com/auth/drive.readonly"]

# Rate limiter: minimum ms between consecutive Google API calls
RATE_LIMIT_DELAY_MS: int = 200

# Max document size in bytes (100 KB); larger docs are truncated
MAX_DOC_SIZE_BYTES: int = 102400

# Max retry attempts for transient Google API failures
MAX_RETRIES: int = 3
