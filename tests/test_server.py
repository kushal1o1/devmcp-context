"""Tests for session-recall auto-logging in the MCP server tool layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from devmcp_context.server import (
    context_log_session_recall,
    context_save,
    context_session_start,
)
from devmcp_context.storage import _session_log_path


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset module-level session flags before each test."""
    import devmcp_context.server as server

    server._session_recall_fired = False
    server._session_recall_logged = False
    yield
    server._session_recall_fired = False
    server._session_recall_logged = False


def _set_project_root(monkeypatch, path: Path):
    monkeypatch.setattr("devmcp_context.server._get_project_root", lambda: path)


class TestAutoLogAtFirstEdit:
    def test_first_save_logs_session(self, temp_project_dir: Path, monkeypatch):
        """First save after session start writes exactly one log row."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()

        result = context_save(category="project", key="goal", value="Ship v1")
        assert result["saved"] is True

        log_path = _session_log_path(temp_project_dir)
        assert log_path.exists()
        rows = _session_log_rows(temp_project_dir)
        assert len(rows) == 1

    def test_single_row_per_session(self, temp_project_dir: Path, monkeypatch):
        """Multiple saves still write only one session row."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()

        context_save(category="project", key="goal", value="Ship v1")
        context_save(category="task", key="fix-x", value="Fix the bug")
        context_save(category="task", key="fix-y", value="Fix the other bug")

        rows = _session_log_rows(temp_project_dir)
        assert len(rows) == 1

    def test_recall_not_fired_logs_false(self, temp_project_dir: Path, monkeypatch):
        """Editing without any recall logs recall fired = false."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()

        context_save(category="project", key="goal", value="Ship v1")

        row = _session_log_rows(temp_project_dir)[0]
        assert "| false |" in row

    def test_recall_fired_logs_true(self, temp_project_dir: Path, monkeypatch):
        """Loading before first edit logs recall fired = true."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()

        from devmcp_context.server import context_load

        context_load(category="project")
        context_save(category="project", key="goal", value="Ship v1")

        row = _session_log_rows(temp_project_dir)[0]
        assert "| true |" in row

    def test_new_session_logs_separately(self, temp_project_dir: Path, monkeypatch):
        """A second session start adds a second row."""
        _set_project_root(monkeypatch, temp_project_dir)

        context_session_start()
        context_save(category="project", key="goal", value="Ship v1")

        context_session_start()
        context_save(category="project", key="goal", value="Ship v2")

        assert len(_session_log_rows(temp_project_dir)) == 2


class TestManualLog:
    def test_log_without_edit(self, temp_project_dir: Path, monkeypatch):
        """Manual logging works for sessions with no edits."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()

        result = context_log_session_recall()
        assert result["logged"] is True
        assert result["recall_fired"] is False
        assert "not logged" not in result["message"]
        assert len(_session_log_rows(temp_project_dir)) == 1

    def test_manual_after_auto_log_no_duplicate(self, temp_project_dir: Path, monkeypatch):
        """Manual logging after an auto-log doesn't add a duplicate row."""
        _set_project_root(monkeypatch, temp_project_dir)
        context_session_start()
        context_save(category="project", key="goal", value="Ship v1")

        result = context_log_session_recall()
        assert result["logged"] is True
        assert "already logged" in result["message"]
        assert len(_session_log_rows(temp_project_dir)) == 1


def _session_log_rows(project_root: Path) -> list[str]:
    log_path = _session_log_path(project_root)
    if not log_path.exists():
        return []
    lines = log_path.read_text().splitlines()
    return [line for line in lines[4:] if line.startswith("|")]
