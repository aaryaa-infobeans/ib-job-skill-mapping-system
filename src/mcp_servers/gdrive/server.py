"""
Google Drive MCP server — FastMCP, STDIO transport.

Exposes three tools:
  - read_document(url, file_id)
  - search_files(query, max_results)
  - get_file_metadata(file_id)

SA credentials are loaded *only* inside this process via config.SA_KEY_PATH.
They are never returned to the MCP client caller.

Entry point:
    python -m src.mcp_servers.gdrive.server
"""

import asyncio
import re
import time
import logging
from typing import Any

from mcp_servers.gdrive import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP import — optional so the module stays importable in tests that mock
# ---------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP  # mcp[cli] >= 1.0
except ImportError:
    from mcp.server import FastMCP  # type: ignore[no-redef]

mcp = FastMCP("gdrive-resume-server")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_last_api_call_ts: float = 0.0


def _rate_limit() -> None:
    """Block until RATE_LIMIT_DELAY_MS has elapsed since the last API call."""
    global _last_api_call_ts
    elapsed_ms = (time.monotonic() - _last_api_call_ts) * 1000
    if elapsed_ms < config.RATE_LIMIT_DELAY_MS:
        time.sleep((config.RATE_LIMIT_DELAY_MS - elapsed_ms) / 1000)
    _last_api_call_ts = time.monotonic()


def _get_credentials():
    """
    Return Google API credentials.

    Priority:
    1. OAuth2 user token (secrets/oauth-token.json) — works within any domain
       as long as the authorizing user has Drive access.
    2. Service account key (GOOGLE_SERVICE_ACCOUNT_FILE) — only works when the
       SA is in an allowlisted domain or files are explicitly shared with it.
    """
    import os
    from googleapiclient.discovery import build

    token_path = config.OAUTH_TOKEN_PATH

    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(token_path, config.DRIVE_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist the refreshed token
            with open(token_path, "w") as fh:
                fh.write(creds.to_json())
        return creds

    # Fallback: service account
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(
        config.SA_KEY_PATH, scopes=config.DRIVE_SCOPES
    )


def _get_drive_service():
    """Build an authenticated Google Drive v3 service."""
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_get_credentials())


def _get_docs_service():
    """Build an authenticated Google Docs v1 service."""
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=_get_credentials())


def _extract_doc_id(url: str) -> str | None:
    """Extract the Google Doc/Drive file ID from a URL or raw ID string."""
    # Matches /d/<id>/ or ?id=<id> or a bare 33–44-char alphanumeric ID
    patterns = [
        r"/d/([a-zA-Z0-9_-]{25,})",
        r"id=([a-zA-Z0-9_-]{25,})",
        r"^([a-zA-Z0-9_-]{25,})$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _read_structural_elements(elements: list) -> str:
    """Recursively extract plain text from Google Docs structural elements."""
    text_parts: list[str] = []
    for element in elements:
        if "paragraph" in element:
            for pe in element["paragraph"].get("elements", []):
                tr = pe.get("textRun")
                if tr:
                    text_parts.append(tr.get("content", ""))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    text_parts.append(
                        _read_structural_elements(cell.get("content", []))
                    )
        elif "tableOfContents" in element:
            text_parts.append(
                _read_structural_elements(
                    element["tableOfContents"].get("content", [])
                )
            )
    return "".join(text_parts)


def _call_with_retries(fn, *args, **kwargs):
    """
    Call `fn(*args, **kwargs)` with exponential back-off.

    Retries up to MAX_RETRIES times (delays: 1s, 2s, 4s) on transient errors.
    Raises the last exception on exhaustion.
    """
    import googleapiclient.errors as ge

    delays = [1, 2, 4]
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays[: config.MAX_RETRIES], start=1):
        try:
            _rate_limit()
            return fn(*args, **kwargs)
        except ge.HttpError as exc:
            # 4xx are not transient — re-raise immediately
            if exc.resp.status in (400, 401, 403, 404):
                raise
            last_exc = exc
            logger.warning(
                "Transient Google API error (attempt %d/%d): %s",
                attempt,
                config.MAX_RETRIES,
                exc,
            )
            time.sleep(delay)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Unexpected error (attempt %d/%d): %s",
                attempt,
                config.MAX_RETRIES,
                exc,
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Google API call failed after {config.MAX_RETRIES} retries"
    ) from last_exc


# ---------------------------------------------------------------------------
# Drive export fallback (for DOCX / Office files stored in Drive)
# ---------------------------------------------------------------------------


def _read_via_drive_export(file_id: str) -> dict:
    """
    Read a non-native Drive file (e.g. uploaded DOCX) as plain text.

    Strategy:
    - Native Google Doc → Drive Files.export(mimeType='text/plain')
    - Binary DOCX/Office file → download raw bytes with get_media(),
      parse paragraphs with python-docx
    """
    import googleapiclient.errors as ge
    import io

    try:
        drive_svc = _get_drive_service()

        # Check MIME type to choose extraction path
        meta = drive_svc.files().get(fileId=file_id, fields="mimeType").execute()
        mime = meta.get("mimeType", "")

        if mime == "application/vnd.google-apps.document":
            # Native Google Doc — use export API
            def _export():
                return (
                    drive_svc.files()
                    .export(fileId=file_id, mimeType="text/plain")
                    .execute()
                )

            raw = _call_with_retries(_export)
            text = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
        else:
            # Binary file (DOCX, DOC, etc.) — download raw and parse
            def _download():
                req = drive_svc.files().get_media(fileId=file_id)
                buf = io.BytesIO()
                from googleapiclient.http import MediaIoBaseDownload
                dl = MediaIoBaseDownload(buf, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
                buf.seek(0)
                return buf.read()

            raw_bytes = _call_with_retries(_download)
            text = _extract_text_from_docx(raw_bytes)

        result: dict = {}
        if len(text.encode("utf-8")) > config.MAX_DOC_SIZE_BYTES:
            text = text.encode("utf-8")[: config.MAX_DOC_SIZE_BYTES].decode(
                "utf-8", errors="ignore"
            )
            result["warning"] = "truncated"

        result["text"] = text
        return result

    except ge.HttpError as exc:
        status = exc.resp.status
        if status == 404:
            return {"error": "not_found", "text": ""}
        if status == 403:
            return {"error": "permission_denied"}
        return {"error": f"http_{status}"}
    except Exception as exc:
        logger.error("_read_via_drive_export unexpected error: %s", exc)
        return {"error": "internal_error"}


def _extract_text_from_docx(raw_bytes: bytes) -> str:
    """Extract plain text from a DOCX file's bytes using python-docx.

    Reads both top-level paragraphs and all table cell content so that
    resumes using table-based layouts are fully extracted. Table cells are
    appended after their containing table so document order is approximated.
    """
    import io
    try:
        from docx import Document

        doc = Document(io.BytesIO(raw_bytes))
        parts: list[str] = []

        def _cell_text(cell) -> str:
            """Recursively extract text from a cell, including nested tables."""
            cell_parts: list[str] = []
            for para in cell.paragraphs:
                if para.text.strip():
                    cell_parts.append(para.text)
            for nested_table in cell.tables:
                for row in nested_table.rows:
                    for nested_cell in row.cells:
                        t = _cell_text(nested_cell)
                        if t:
                            cell_parts.append(t)
            return "\n".join(cell_parts)

        # Iterate body children in document order so paragraphs and tables
        # appear in the correct sequence (python-docx doc.paragraphs and
        # doc.tables are separate flat lists that lose interleaving).
        body = doc.element.body
        for child in body:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "p":
                from docx.text.paragraph import Paragraph
                para = Paragraph(child, doc)
                if para.text.strip():
                    parts.append(para.text)
            elif tag == "tbl":
                from docx.table import Table
                table = Table(child, doc)
                for row in table.rows:
                    for cell in row.cells:
                        t = _cell_text(cell)
                        if t:
                            parts.append(t)

        return "\n".join(parts)
    except Exception as exc:
        logger.warning("DOCX parse failed, returning empty text: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def read_document(url: str, file_id: str = "") -> dict[str, Any]:
    """
    Fetch the plain-text content of a Google Doc.

    Args:
        url: Google Doc URL (used to extract file ID if file_id not provided)
        file_id: Optional explicit file ID (takes precedence over url)

    Returns:
        {"text": "<content>"} on success, or {"error": "<code>"} on failure.
        {"warning": "truncated"} is added when the document exceeds 100 KB.
    """
    import googleapiclient.errors as ge

    doc_id = file_id or _extract_doc_id(url)
    if not doc_id:
        return {"error": "invalid_url", "text": ""}

    try:
        docs_svc = _get_docs_service()

        def _fetch():
            return docs_svc.documents().get(documentId=doc_id).execute()

        doc = _call_with_retries(_fetch)
        body = doc.get("body", {})
        text = _read_structural_elements(body.get("content", []))

        result: dict[str, Any] = {}
        if len(text.encode("utf-8")) > config.MAX_DOC_SIZE_BYTES:
            text = text.encode("utf-8")[: config.MAX_DOC_SIZE_BYTES].decode(
                "utf-8", errors="ignore"
            )
            result["warning"] = "truncated"

        result["text"] = text
        return result

    except ge.HttpError as exc:
        status = exc.resp.status
        if status == 404:
            return {"error": "not_found", "text": ""}
        if status == 403:
            return {"error": "permission_denied"}
        if status == 400:
            # File is not a native Google Doc (e.g. DOCX with rtpof=true).
            # Fall back to Drive Files export API which converts to plain text.
            return _read_via_drive_export(doc_id)
        return {"error": f"http_{status}"}
    except RuntimeError:
        return {"error": "quota_exceeded"}
    except Exception as exc:
        logger.error("read_document unexpected error: %s", exc)
        return {"error": "internal_error"}


@mcp.tool()
def search_files(query: str, max_results: int = 10) -> dict[str, Any]:
    """
    Search Google Drive files by query string.

    Args:
        query: Drive search query (e.g. "name contains 'resume'")
        max_results: Maximum number of results (default 10, max 100)

    Returns:
        {"files": [{"id": ..., "name": ..., "mimeType": ...}, ...]}
    """
    import googleapiclient.errors as ge

    max_results = min(max(1, max_results), 100)

    try:
        drive_svc = _get_drive_service()

        def _search():
            return (
                drive_svc.files()
                .list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id, name, mimeType, modifiedTime)",
                )
                .execute()
            )

        result = _call_with_retries(_search)
        return {"files": result.get("files", [])}

    except ge.HttpError as exc:
        status = exc.resp.status
        if status == 403:
            return {"error": "permission_denied", "files": []}
        return {"error": f"http_{status}", "files": []}
    except RuntimeError:
        return {"error": "quota_exceeded", "files": []}
    except Exception as exc:
        logger.error("search_files unexpected error: %s", exc)
        return {"error": "internal_error", "files": []}


@mcp.tool()
def get_file_metadata(file_id: str) -> dict[str, Any]:
    """
    Retrieve metadata for a single Drive file.

    Args:
        file_id: Google Drive file ID

    Returns:
        Metadata dict with id, name, mimeType, modifiedTime, size, owners.
    """
    import googleapiclient.errors as ge

    try:
        drive_svc = _get_drive_service()

        def _meta():
            return (
                drive_svc.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, modifiedTime, size, owners",
                )
                .execute()
            )

        return _call_with_retries(_meta)

    except ge.HttpError as exc:
        status = exc.resp.status
        if status == 404:
            return {"error": "not_found"}
        if status == 403:
            return {"error": "permission_denied"}
        return {"error": f"http_{status}"}
    except RuntimeError:
        return {"error": "quota_exceeded"}
    except Exception as exc:
        logger.error("get_file_metadata unexpected error: %s", exc)
        return {"error": "internal_error"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
