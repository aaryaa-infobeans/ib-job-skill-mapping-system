"""
MCPResumeClient — STDIO MCP client for fetching Google Drive resume documents.

Key design decisions:
- SA credentials are passed ONLY to the MCP server subprocess env.
  The cron process os.environ never contains GOOGLE_SERVICE_ACCOUNT_FILE.
- Session-per-batch: one MCP session is held open for all members in a batch
  to amortize the ~500ms subprocess init cost.
- Broken-pipe recovery: up to 3 reconnect attempts; returns None after exhaustion
  (never raises). Cron sets EXIT_PARTIAL (1) if some members failed.

TASK-EMB-021 | TASK-EMB-022 | Plan §6.1-6.4 | CR §3.4.2 | AC-14, AC-15 | R9, R12
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_DELAY_S = 2.0

# ---------------------------------------------------------------------------
# Metric counters (emitted as structured log events — TASK-EMB-036)
# ---------------------------------------------------------------------------
_METRICS = {
    "mcp_session_init_duration_seconds": 0.0,
    "mcp_tool_call_total": 0,
    "mcp_tool_call_error_total": 0,
}


class MCPResumeClient:
    """
    Async/sync MCP client that fetches resume text from Google Drive.

    Usage (sync — typical cron path):
        client = MCPResumeClient(server_script="src/mcp_servers/gdrive/server.py")
        with client.batch_session() as sess:
            text = client.fetch_resume_sync("https://docs.google.com/...")
    """

    def __init__(
        self,
        server_script: str = "src/mcp_servers/gdrive/server.py",
        sa_key_path: Optional[str] = None,
    ) -> None:
        """
        Args:
            server_script: Path to the FastMCP server script.
            sa_key_path: Override SA key path; default reads from env
                         GOOGLE_SERVICE_ACCOUNT_FILE at call time (AC-14).
        """
        self.server_script = server_script
        self._sa_key_path = sa_key_path
        self._session = None
        self._stdio_cm = None

    # ------------------------------------------------------------------
    # Internal: build StdioServerParameters with SA key in subprocess env
    # ------------------------------------------------------------------

    def _make_server_params(self):
        """Build StdioServerParameters. SA key injected into subprocess env."""
        from mcp import StdioServerParameters

        sa_key = self._sa_key_path or os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_FILE", ""
        )

        # Inherit full parent env so subprocess has PATH, PYTHONPATH, TEMP, etc.
        # Then override/add the SA key so it's visible to the MCP server.
        subprocess_env = dict(os.environ)
        if sa_key:
            subprocess_env["GOOGLE_SERVICE_ACCOUNT_FILE"] = sa_key
        else:
            subprocess_env.pop("GOOGLE_SERVICE_ACCOUNT_FILE", None)

        return StdioServerParameters(
            command="python",
            args=[self.server_script],
            env=subprocess_env,
        )

    # ------------------------------------------------------------------
    # Async core
    # ------------------------------------------------------------------

    async def _open_session(self):
        """Start MCP subprocess and initialize session. Returns session."""
        from mcp import ClientSession, stdio_client

        t0 = time.monotonic()
        server_params = self._make_server_params()
        self._stdio_cm = stdio_client(server_params)
        read, write = await self._stdio_cm.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        elapsed = time.monotonic() - t0
        logger.info(
            "mcp_session_init_duration_seconds",
            metric="mcp_session_init_duration_seconds",
            server="gdrive",
            value=round(elapsed, 3),
        )
        return session

    async def _close_session(self, session):
        """Tear down session and subprocess."""
        try:
            if session:
                await session.__aexit__(None, None, None)
            if self._stdio_cm:
                await self._stdio_cm.__aexit__(None, None, None)
        except Exception:
            pass
        self._session = None
        self._stdio_cm = None

    async def fetch_resume(
        self, profile_url: str, _retries: int = 0
    ) -> Optional[dict]:
        """
        Async: fetch resume text via read_document MCP tool.

        Args:
            profile_url: Google Doc URL.
            _retries: Internal retry counter.

        Returns:
            dict with "text" key, or None on failure.
        """
        if self._session is None:
            self._session = await self._open_session()

        try:
            result = await self._session.call_tool(
                "read_document", {"url": profile_url, "file_id": ""}
            )
            logger.info(
                "mcp_tool_call_total",
                metric="mcp_tool_call_total",
                tool="read_document",
                status="success",
            )
            # result.content is a list of TextContent
            payload = {}
            if hasattr(result, "content") and result.content:
                import json

                raw = result.content[0].text if hasattr(result.content[0], "text") else "{}"
                try:
                    payload = json.loads(raw)
                except (ValueError, TypeError):
                    payload = {"text": str(raw)}
            return payload

        except BrokenPipeError as exc:
            return await self._handle_connection_error(
                profile_url, exc, "broken_pipe", _retries
            )
        except ConnectionError as exc:
            return await self._handle_connection_error(
                profile_url, exc, "crash", _retries
            )
        except Exception as exc:
            logger.warning(
                "mcp_tool_call_error_total",
                metric="mcp_tool_call_error_total",
                error_type="internal_error",
                error=str(exc),
            )
            return None

    async def _handle_connection_error(
        self, profile_url: str, exc: Exception, error_type: str, retries: int
    ) -> Optional[dict]:
        """Attempt reconnect up to _MAX_RECONNECT_ATTEMPTS times."""
        logger.warning(
            "mcp_tool_call_error_total",
            metric="mcp_tool_call_error_total",
            error_type=error_type,
            attempt=retries + 1,
            error=str(exc),
        )
        await self._close_session(self._session)

        if retries >= _MAX_RECONNECT_ATTEMPTS - 1:
            logger.error(
                "MCP server unreachable after %d retries; giving up",
                _MAX_RECONNECT_ATTEMPTS,
            )
            return None

        await asyncio.sleep(_RECONNECT_DELAY_S)
        return await self.fetch_resume(profile_url, _retries=retries + 1)

    # ------------------------------------------------------------------
    # Sync wrapper (cron entry point)
    # ------------------------------------------------------------------

    def fetch_resume_sync(self, profile_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Sync wrapper around fetch_resume().

        Each call uses its own asyncio event loop (via asyncio.run), so the MCP
        session opened in one call cannot be reused in the next. Session state
        is cleared after every call to ensure a fresh session is opened.

        Returns:
            (text, error_code) where text is the resume content (or None) and
            error_code is the reason string on failure (e.g. "permission_denied",
            "not_found", "invalid_url") or None on success.
        """
        try:
            result = asyncio.run(self.fetch_resume(profile_url))
        finally:
            # asyncio.run() creates and closes a new event loop; any session
            # opened inside that loop is now invalid. Clear state so the next
            # call opens a fresh session in its own loop.
            self._session = None
            self._stdio_cm = None
        if result is None:
            return None, "mcp_call_failed"
        text = result.get("text", "")
        if text:
            return text, None
        error_code = result.get("error", "empty_text")
        return None, error_code

    # ------------------------------------------------------------------
    # Batch session context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        """Open MCP session for batch processing."""
        return self

    def __exit__(self, *args):
        """Close MCP session."""
        if self._session is not None:
            try:
                asyncio.run(self._close_session(self._session))
            except Exception:
                pass
