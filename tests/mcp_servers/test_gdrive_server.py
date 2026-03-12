"""
Unit tests for MCP Google Drive server (TASK-EMB-005).

All Google API calls are mocked — no SA key, DB, or network required.
Run:  pytest tests/mcp_servers/test_gdrive_server.py -v
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Ensure src/ is on the path so `mcp_servers` package is importable
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers to build realistic mock Google API responses
# ---------------------------------------------------------------------------

def _make_doc_response(text: str = "Resume content here.") -> dict:
    return {
        "documentId": "fakeid123",
        "title": "Resume",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": text}}]
                    }
                }
            ]
        },
    }


def _make_drive_files_response(items: list | None = None) -> dict:
    return {
        "files": items
        or [
            {
                "id": "file1",
                "name": "resume.docx",
                "mimeType": "application/vnd.google-apps.document",
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGDriveServer(unittest.TestCase):

    # ---- tool registration ------------------------------------------------

    def test_tools_list_returns_three_tools(self):
        """AC-12: FastMCP instance exposes exactly 3 tools."""
        from mcp_servers.gdrive.server import mcp

        tools = mcp._tool_manager._tools  # internal registry
        tool_names = set(tools.keys())
        self.assertIn("read_document", tool_names)
        self.assertIn("search_files", tool_names)
        self.assertIn("get_file_metadata", tool_names)
        self.assertEqual(len(tool_names), 3)

    # ---- read_document ----------------------------------------------------

    @patch("mcp_servers.gdrive.server._get_docs_service")
    def test_read_document_happy_path_google_doc(self, mock_get_svc):
        """Happy path: Google Doc returns plain text."""
        from mcp_servers.gdrive.server import read_document

        mock_docs = MagicMock()
        mock_docs.documents().get().execute.return_value = _make_doc_response(
            "Resume content here."
        )
        mock_get_svc.return_value = mock_docs

        result = read_document(
            url="https://docs.google.com/document/d/fakeid123/edit",
            file_id="fakeid123",
        )
        self.assertIn("text", result)
        self.assertIn("Resume content here.", result["text"])

    def test_read_document_file_id_extraction(self):
        """File ID extracted from URL when file_id arg is empty."""
        from mcp_servers.gdrive.server import _extract_doc_id

        fid = _extract_doc_id(
            "https://docs.google.com/document/d/ABCDEFGHIJ1234567890abcde/edit"
        )
        self.assertEqual(fid, "ABCDEFGHIJ1234567890abcde")

    def test_read_document_invalid_url_returns_error(self):
        """Invalid URL (no file ID) returns error dict."""
        from mcp_servers.gdrive.server import read_document

        result = read_document(url="https://example.com/notadoc", file_id="")
        self.assertEqual(result.get("error"), "invalid_url")

    @patch("mcp_servers.gdrive.server._get_docs_service")
    def test_read_document_404_returns_not_found(self, mock_get_svc):
        """HTTP 404 from Docs API returns {error: not_found}."""
        import googleapiclient.errors as ge
        import httplib2

        from mcp_servers.gdrive.server import read_document

        mock_docs = MagicMock()
        resp = httplib2.Response({"status": 404})
        mock_docs.documents().get().execute.side_effect = ge.HttpError(
            resp=resp, content=b"Not Found"
        )
        mock_get_svc.return_value = mock_docs

        result = read_document(url="x", file_id="badid12345678901234567890")
        self.assertEqual(result.get("error"), "not_found")

    @patch("mcp_servers.gdrive.server._get_docs_service")
    def test_read_document_403_returns_permission_denied(self, mock_get_svc):
        """HTTP 403 returns {error: permission_denied}."""
        import googleapiclient.errors as ge
        import httplib2

        from mcp_servers.gdrive.server import read_document

        mock_docs = MagicMock()
        resp = httplib2.Response({"status": 403})
        mock_docs.documents().get().execute.side_effect = ge.HttpError(
            resp=resp, content=b"Forbidden"
        )
        mock_get_svc.return_value = mock_docs

        result = read_document(url="x", file_id="badid12345678901234567890")
        self.assertEqual(result.get("error"), "permission_denied")

    @patch("mcp_servers.gdrive.server._get_docs_service")
    def test_read_document_oversized_truncates_at_100kb(self, mock_get_svc):
        """Documents > 100 KB are truncated and warning key added."""
        from mcp_servers.gdrive.server import read_document
        from mcp_servers.gdrive import config

        big_text = "x" * (config.MAX_DOC_SIZE_BYTES + 5000)
        mock_docs = MagicMock()
        mock_docs.documents().get().execute.return_value = _make_doc_response(
            big_text
        )
        mock_get_svc.return_value = mock_docs

        result = read_document(url="x", file_id="docid12345678901234567890")
        self.assertIn("warning", result)
        self.assertLessEqual(
            len(result["text"].encode("utf-8")), config.MAX_DOC_SIZE_BYTES
        )

    # ---- search_files -----------------------------------------------------

    @patch("mcp_servers.gdrive.server._get_drive_service")
    def test_search_files_returns_file_list(self, mock_get_svc):
        """search_files returns a list under 'files' key."""
        from mcp_servers.gdrive.server import search_files

        mock_drive = MagicMock()
        mock_drive.files().list().execute.return_value = (
            _make_drive_files_response()
        )
        mock_get_svc.return_value = mock_drive

        result = search_files(query="resume", max_results=5)
        self.assertIn("files", result)
        self.assertIsInstance(result["files"], list)
        self.assertGreater(len(result["files"]), 0)

    # ---- get_file_metadata ------------------------------------------------

    @patch("mcp_servers.gdrive.server._get_drive_service")
    def test_get_file_metadata_returns_dict(self, mock_get_svc):
        """get_file_metadata returns a dict with id and name."""
        from mcp_servers.gdrive.server import get_file_metadata

        mock_drive = MagicMock()
        mock_drive.files().get().execute.return_value = {
            "id": "file1",
            "name": "resume.docx",
            "mimeType": "application/vnd.google-apps.document",
        }
        mock_get_svc.return_value = mock_drive

        result = get_file_metadata(file_id="file1")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("id"), "file1")

    # ---- config -----------------------------------------------------------

    def test_auth_config_reads_env_var(self):
        """SA_KEY_PATH is overridable via GOOGLE_SERVICE_ACCOUNT_FILE env var."""
        import importlib

        with patch.dict(
            os.environ, {"GOOGLE_SERVICE_ACCOUNT_FILE": "/tmp/test-sa.json"}
        ):
            import mcp_servers.gdrive.config as cfg  # noqa: F401

            importlib.reload(cfg)
            self.assertEqual(cfg.SA_KEY_PATH, "/tmp/test-sa.json")


if __name__ == "__main__":
    unittest.main()
