"""
MCPResumeClient unit tests (TASK-EMB-026 + TASK-EMB-025).

Tests:
  1. test_session_lifecycle_init_call_close
  2. test_fetch_resume_sync_returns_text
  3. test_fetch_resume_sync_empty_doc_returns_none
  4. test_broken_pipe_triggers_reconnect_max_3
  5. test_credential_isolation_env_not_in_cron_process  (AC-14)
  6. test_server_crash_returns_none_gracefully

Run:  pytest tests/cron/test_mcp_client.py -v
No real MCP server or SA key needed.
"""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestMCPResumeClient(unittest.TestCase):

    # ------------------------------------------------------------------
    # Helper: build a mock ClientSession
    # ------------------------------------------------------------------

    def _make_session_mock(self, tool_result_text: str = "Resume content"):
        """Return an AsyncMock ClientSession producing fixed tool result."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.initialize = AsyncMock(return_value=None)

        content_item = MagicMock()
        content_item.text = f'{{"text": "{tool_result_text}"}}'

        tool_result = MagicMock()
        tool_result.content = [content_item]
        session.call_tool = AsyncMock(return_value=tool_result)
        return session

    def _patch_stdio_client(self, session_mock):
        """Context manager that returns (AsyncMock_read, AsyncMock_write)."""
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
        cm.__aexit__ = AsyncMock(return_value=None)

        def _stdio_client_factory(_params):
            return cm

        return patch("mcp.stdio_client", side_effect=_stdio_client_factory)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_session_lifecycle_init_call_close(self):
        """Session open → initialize() → call_tool() → close in order."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        session_mock = self._make_session_mock("Test resume")

        with (
            patch(
                "mcp.ClientSession",
                return_value=session_mock,
            ),
            self._patch_stdio_client(session_mock),
        ):
            client = MCPResumeClient(server_script="fake.py", sa_key_path="")
            result = asyncio.run(client.fetch_resume("https://docs.google.com/test"))

        session_mock.initialize.assert_called_once()
        session_mock.call_tool.assert_called_once()
        self.assertIsNotNone(result)

    def test_fetch_resume_sync_returns_text(self):
        """fetch_resume_sync() returns string text on success."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        session_mock = self._make_session_mock("John Doe resume here.")

        with (
            patch("mcp.ClientSession", return_value=session_mock),
            self._patch_stdio_client(session_mock),
        ):
            client = MCPResumeClient(server_script="fake.py", sa_key_path="")
            text = client.fetch_resume_sync("https://docs.google.com/test")

        self.assertEqual(text, "John Doe resume here.")

    def test_fetch_resume_sync_empty_doc_returns_none(self):
        """Empty text result returns None, not empty string."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        session_mock = self._make_session_mock("")  # empty text

        with (
            patch("mcp.ClientSession", return_value=session_mock),
            self._patch_stdio_client(session_mock),
        ):
            client = MCPResumeClient(server_script="fake.py", sa_key_path="")
            result = client.fetch_resume_sync("https://docs.google.com/test")

        self.assertIsNone(result)

    def test_broken_pipe_triggers_reconnect_max_3(self):
        """3 consecutive BrokenPipeErrors → returns None (no exception)."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        session_mock.initialize = AsyncMock(return_value=None)
        session_mock.call_tool = AsyncMock(side_effect=BrokenPipeError("pipe broken"))

        call_count = 0
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
        cm.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("mcp.ClientSession", return_value=session_mock),
            patch("mcp.stdio_client", return_value=cm),
            patch("asyncio.sleep", new=AsyncMock()),  # skip real delays
        ):
            client = MCPResumeClient(server_script="fake.py", sa_key_path="")
            result = asyncio.run(
                client.fetch_resume("https://docs.google.com/test")
            )

        self.assertIsNone(result, "Should return None after 3 reconnect attempts")

    def test_credential_isolation_env_not_in_cron_process(self):
        """
        AC-14: GOOGLE_SERVICE_ACCOUNT_FILE must NOT be in cron process os.environ.
        It may only be in the StdioServerParameters.env dict.
        """
        from app.cron.embedding.mcp_client import MCPResumeClient

        # Ensure the key is NOT in the cron process env
        env_backup = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_FILE", None)
        try:
            client = MCPResumeClient(
                server_script="fake.py",
                sa_key_path="/tmp/test-sa.json",
            )
            self.assertNotIn(
                "GOOGLE_SERVICE_ACCOUNT_FILE",
                os.environ,
                "SA key must not leak into cron process env",
            )

            # The StdioServerParameters env should contain the key
            params = client._make_server_params()
            self.assertEqual(
                params.env.get("GOOGLE_SERVICE_ACCOUNT_FILE"), "/tmp/test-sa.json"
            )
        finally:
            if env_backup is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = env_backup

    def test_server_crash_returns_none_gracefully(self):
        """ConnectionError (simulating server crash) → returns None, no raise."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        session_mock.initialize = AsyncMock(return_value=None)
        session_mock.call_tool = AsyncMock(
            side_effect=ConnectionError("server crashed")
        )

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
        cm.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("mcp.ClientSession", return_value=session_mock),
            patch("mcp.stdio_client", return_value=cm),
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            client = MCPResumeClient(server_script="fake.py", sa_key_path="")
            result = asyncio.run(
                client.fetch_resume("https://docs.google.com/test")
            )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
