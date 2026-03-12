"""
One-time OAuth2 setup for Google Drive MCP server.

Run this script once to authorize a Google account that has access to the
InfoBeans Drive folder containing resumes.  It opens a browser consent page,
then saves a token to secrets/oauth-token.json.  The MCP server will use that
token automatically on every subsequent run (auto-refreshing when it expires).

Usage
-----
    python scripts/setup_gdrive_oauth.py

Requirements
------------
1.  Create an OAuth 2.0 "Desktop app" credential in Google Cloud Console:
      https://console.cloud.google.com/apis/credentials
    Download the JSON and save it as  secrets/oauth-client-secrets.json

2.  Enable the Google Drive API and Google Docs API for the project:
      https://console.cloud.google.com/apis/library

3.  Run this script and sign in with your InfoBeans Google account.
    The account only needs Viewer access to the Drive folder/files.

Output
------
    secrets/oauth-token.json   (gitignored — never commit this)

Environment overrides
---------------------
    GOOGLE_OAUTH_CLIENT_SECRETS_FILE  — path to client secrets JSON
    GOOGLE_OAUTH_TOKEN_FILE           — path to write the token
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = REPO_ROOT / "secrets"
DEFAULT_CLIENT_SECRETS = SECRETS_DIR / "oauth-client-secrets.json"
DEFAULT_TOKEN_PATH = SECRETS_DIR / "oauth-token.json"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def check_dependencies() -> None:
    missing = []
    for pkg in ("google.oauth2", "google_auth_oauthlib", "googleapiclient"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing packages: {missing}")
        print("       Run:  pip install google-auth google-auth-oauthlib google-api-python-client")
        sys.exit(1)


def get_paths() -> tuple[Path, Path]:
    client_secrets = Path(
        os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS_FILE", str(DEFAULT_CLIENT_SECRETS))
    )
    token_path = Path(
        os.environ.get("GOOGLE_OAUTH_TOKEN_FILE", str(DEFAULT_TOKEN_PATH))
    )
    return client_secrets, token_path


def run_oauth_flow(client_secrets: Path, token_path: Path) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    print(f"\n[1/3] Using client secrets: {client_secrets}")
    if not client_secrets.exists():
        print(
            "\n[ERROR] Client secrets file not found.\n"
            "        Steps to create one:\n"
            "          1. Go to https://console.cloud.google.com/apis/credentials\n"
            "          2. Click 'Create Credentials' → 'OAuth client ID'\n"
            "          3. Choose 'Desktop app', name it (e.g. 'gdrive-mcp')\n"
            "          4. Download the JSON and save it as:\n"
            f"             {client_secrets}\n"
        )
        sys.exit(1)

    print("[2/3] Opening browser for Google OAuth consent…")
    print("      Sign in with the InfoBeans account that has Drive access.\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    print(f"[3/3] Token saved to: {token_path}")


def smoke_test(token_path: Path) -> None:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    print("\n[smoke test] Verifying Drive API access…")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    svc = build("drive", "v3", credentials=creds)
    result = svc.files().list(pageSize=5, fields="files(id,name)").execute()
    files = result.get("files", [])
    print(f"  Drive API OK — {len(files)} file(s) visible to this account.")
    for f in files[:5]:
        print(f"    {f['id']}  {f['name']}")

    # Update .env with token path
    _upsert_env(token_path)


def _upsert_env(token_path: Path) -> None:
    env_file = REPO_ROOT / ".env"
    key = "GOOGLE_OAUTH_TOKEN_FILE"
    value = str(token_path)

    if not env_file.exists():
        env_file.write_text(f"{key}={value}\n")
        print(f"\n[.env] Created with {key}={value}")
        return

    lines = env_file.read_text().splitlines(keepends=True)
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break

    if not updated:
        lines.append(f"\n{key}={value}\n")

    env_file.write_text("".join(lines))
    print(f"\n[.env] Set {key}={value}")


def main() -> None:
    print("=== Google Drive OAuth2 Setup ===")
    check_dependencies()
    client_secrets, token_path = get_paths()

    if token_path.exists():
        print(f"\n[INFO] Token already exists at: {token_path}")
        resp = input("  Re-authorize? [y/N] ").strip().lower()
        if resp != "y":
            smoke_test(token_path)
            return

    run_oauth_flow(client_secrets, token_path)
    smoke_test(token_path)
    print("\n✓ Setup complete. Run:  python -m app.cron embed --force")


if __name__ == "__main__":
    main()
