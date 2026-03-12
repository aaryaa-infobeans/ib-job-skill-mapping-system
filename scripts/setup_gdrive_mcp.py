"""
Setup script for the Google Drive MCP server.

Steps performed:
  1. Check required Python packages are importable.
  2. Resolve the service-account key file path (env-override or default).
  3. Create the secrets directory if it doesn't exist.
  4. Prompt the user to place the key file if it's missing.
  5. Validate the key file has the expected structure.
  6. Smoke-test a live Google Drive API connection.
  7. Print an MCP client config snippet ready to paste into claude_desktop_config.json.

Usage:
    python scripts/setup_gdrive_mcp.py [--key-path /path/to/sa-key.json]

Environment variables (override defaults):
    GOOGLE_SERVICE_ACCOUNT_FILE  – path to the service-account JSON key file
                                   (default: ./secrets/sa-key.json)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = [
    ("google.oauth2.service_account", "google-auth>=2.28"),
    ("googleapiclient.discovery", "google-api-python-client>=2.120"),
    ("mcp.server.fastmcp", "mcp[cli]>=1.0"),
]

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

REQUIRED_SA_FIELDS = {
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "token_uri",
}

DEFAULT_KEY_PATH = Path("secrets") / "sa-key.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _info(msg: str) -> None:
    print(f"  [--]  {msg}")


def _warn(msg: str) -> None:
    print(f"  [!!]  {msg}", file=sys.stderr)


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1 – dependency check
# ---------------------------------------------------------------------------


def check_dependencies() -> None:
    print("\n=== Step 1: Checking Python dependencies ===")
    missing: list[str] = []
    for module, install_name in REQUIRED_PACKAGES:
        try:
            __import__(module)
            _ok(f"{module}")
        except ImportError:
            _warn(f"{module} not found  →  pip install '{install_name}'")
            missing.append(install_name)

    if missing:
        _fail(
            "Install missing packages then re-run:\n"
            f"    pip install {' '.join(repr(p) for p in missing)}"
        )


# ---------------------------------------------------------------------------
# Step 2 – resolve key path
# ---------------------------------------------------------------------------


def resolve_key_path(cli_path: str | None) -> Path:
    print("\n=== Step 2: Resolving service-account key path ===")

    if cli_path:
        key_path = Path(cli_path).expanduser().resolve()
        _info(f"Using CLI argument: {key_path}")
    elif env := os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE"):
        key_path = Path(env).expanduser().resolve()
        _info(f"Using GOOGLE_SERVICE_ACCOUNT_FILE env var: {key_path}")
    else:
        key_path = Path.cwd() / DEFAULT_KEY_PATH
        _info(f"Using default path: {key_path}")

    return key_path


# ---------------------------------------------------------------------------
# Step 3 – create secrets directory
# ---------------------------------------------------------------------------


def ensure_secrets_dir(key_path: Path) -> None:
    print("\n=== Step 3: Ensuring secrets directory exists ===")
    secrets_dir = key_path.parent
    secrets_dir.mkdir(parents=True, exist_ok=True)
    _ok(f"Directory ready: {secrets_dir}")

    # Warn if the directory is not git-ignored
    gitignore = Path.cwd() / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        relative_dir = secrets_dir.relative_to(Path.cwd()) if secrets_dir.is_relative_to(Path.cwd()) else secrets_dir
        if str(relative_dir) not in content and "secrets/" not in content:
            _warn(
                f"'{relative_dir}' does not appear in .gitignore. "
                "Add it to avoid accidentally committing credentials."
            )


# ---------------------------------------------------------------------------
# Step 4 – check key file presence
# ---------------------------------------------------------------------------


def check_key_file_present(key_path: Path) -> None:
    print("\n=== Step 4: Checking key file presence ===")
    if key_path.exists():
        _ok(f"Key file found: {key_path}")
        return

    _warn(f"Key file not found at: {key_path}")
    print(
        """
  To create a service-account key:
    1. Open https://console.cloud.google.com/apis/library/drive.googleapis.com
       and enable the Google Drive API for your project.
    2. Go to IAM & Admin → Service Accounts → Create Service Account.
    3. Grant it the role "Viewer" (or a custom role with drive.files.list +
       drive.files.get + docs.documents.get).
    4. Open the service account → Keys → Add Key → JSON.
    5. Save the downloaded JSON to:
"""
    )
    print(f"       {key_path}\n")
    _fail("Re-run this script after placing the key file.")


# ---------------------------------------------------------------------------
# Step 5 – validate key file structure
# ---------------------------------------------------------------------------


def validate_key_file(key_path: Path) -> dict:
    print("\n=== Step 5: Validating key file structure ===")
    try:
        data = json.loads(key_path.read_text())
    except json.JSONDecodeError as exc:
        _fail(f"Key file is not valid JSON: {exc}")

    missing = REQUIRED_SA_FIELDS - set(data.keys())
    if missing:
        _fail(f"Key file is missing required fields: {missing}")

    if data.get("type") != "service_account":
        _fail(f"Expected type='service_account', got '{data.get('type')}'")

    _ok(f"Service account: {data['client_email']}")
    _ok(f"Project:         {data['project_id']}")
    return data


# ---------------------------------------------------------------------------
# Step 6 – smoke-test live API connection
# ---------------------------------------------------------------------------


def smoke_test(key_path: Path) -> None:
    print("\n=== Step 6: Testing Google Drive API connection ===")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        _warn("Skipping live test (google packages not importable).")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(key_path), scopes=DRIVE_SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        result = service.files().list(pageSize=1, fields="files(id)").execute()
        count = len(result.get("files", []))
        _ok(f"Connected successfully. Files visible to service account: {count}+")
    except HttpError as exc:
        if exc.resp.status == 403:
            _warn(
                "Got 403 Forbidden. The service account may not have access to any "
                "Drive files yet. Share relevant folders/files with the service account "
                f"email shown above and try again. (Original: {exc})"
            )
        else:
            _fail(f"Google API error {exc.resp.status}: {exc}")
    except Exception as exc:
        _fail(f"Unexpected error during API test: {exc}")


# ---------------------------------------------------------------------------
# Step 7 – print MCP client config snippet
# ---------------------------------------------------------------------------


def print_mcp_config(key_path: Path) -> None:
    print("\n=== Step 7: MCP client configuration snippet ===")

    python_exec = sys.executable
    module_path = "src.mcp_servers.gdrive.server"

    snippet = {
        "mcpServers": {
            "gdrive-resume-server": {
                "command": python_exec,
                "args": ["-m", module_path],
                "env": {
                    "GOOGLE_SERVICE_ACCOUNT_FILE": str(key_path),
                    "PYTHONPATH": str(Path.cwd() / "src"),
                },
            }
        }
    }

    print(
        "\n  Paste this block into your MCP client config "
        "(e.g. claude_desktop_config.json):\n"
    )
    print(json.dumps(snippet, indent=2))
    print(
        "\n  Default config locations:\n"
        "    macOS  : ~/Library/Application Support/Claude/claude_desktop_config.json\n"
        "    Windows: %APPDATA%\\Claude\\claude_desktop_config.json\n"
        "    Linux  : ~/.config/claude/claude_desktop_config.json\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up the Google Drive MCP server for this project."
    )
    parser.add_argument(
        "--key-path",
        metavar="PATH",
        help="Path to the Google service-account JSON key file "
        f"(default: {DEFAULT_KEY_PATH})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Google Drive MCP Server – Setup")
    print("=" * 60)

    check_dependencies()
    key_path = resolve_key_path(args.key_path)
    ensure_secrets_dir(key_path)
    check_key_file_present(key_path)
    validate_key_file(key_path)
    smoke_test(key_path)
    print_mcp_config(key_path)

    print("\n" + "=" * 60)
    print("  Setup complete. The Google Drive MCP server is ready.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
