"""Tests for devmcp_context.init module."""

from __future__ import annotations

import json
from pathlib import Path

from devmcp_context.init import (
    _build_claude_entry,
    _build_cursor_entry,
    _build_opencode_entry,
    _detect_client,
    _entry_name_for_project,
    _find_context_entries,
    _generate_generic_snippet,
    _get_config_path,
    _is_context_entry,
    _read_config,
    _write_config,
    run_init,
)


class TestDetectClient:
    """Tests for client auto-detection."""

    def test_detect_opencode(self, temp_project_dir: Path):
        """Detects opencode when opencode.json exists."""
        (temp_project_dir / "opencode.json").write_text("{}")
        assert _detect_client(temp_project_dir) == "opencode"

    def test_detect_opencode_jsonc(self, temp_project_dir: Path):
        """Detects opencode when opencode.jsonc exists."""
        (temp_project_dir / "opencode.jsonc").write_text("{}")
        assert _detect_client(temp_project_dir) == "opencode"

    def test_detect_cursor(self, temp_project_dir: Path):
        """Detects cursor when .cursor/mcp.json exists."""
        cursor_dir = temp_project_dir / ".cursor"
        cursor_dir.mkdir()
        (cursor_dir / "mcp.json").write_text("{}")
        assert _detect_client(temp_project_dir) == "cursor"

    def test_detect_none(self, temp_project_dir: Path):
        """Returns None when no client config is found."""
        assert _detect_client(temp_project_dir) is None


class TestConfigReadWrite:
    """Tests for config file reading and writing."""

    def test_read_config_missing(self, temp_project_dir: Path):
        """Reading a missing config returns empty dict."""
        assert _read_config(temp_project_dir / "nonexistent.json") == {}

    def test_read_config_empty(self, temp_project_dir: Path):
        """Reading an empty config returns empty dict."""
        path = temp_project_dir / "empty.json"
        path.write_text("")
        assert _read_config(path) == {}

    def test_read_config_valid(self, temp_project_dir: Path):
        """Reading a valid JSON config returns the dict."""
        path = temp_project_dir / "config.json"
        path.write_text('{"key": "value"}')
        assert _read_config(path) == {"key": "value"}

    def test_read_config_invalid_json(self, temp_project_dir: Path):
        """Reading invalid JSON returns empty dict."""
        path = temp_project_dir / "bad.json"
        path.write_text("not json {{{")
        assert _read_config(path) == {}

    def test_write_config_creates_parent(self, temp_project_dir: Path):
        """Writing config creates parent directories."""
        path = temp_project_dir / "subdir" / "config.json"
        _write_config(path, {"hello": "world"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"hello": "world"}

    def test_write_config_creates_valid_json(self, temp_project_dir: Path):
        """Written config is valid JSON."""
        path = temp_project_dir / "config.json"
        _write_config(path, {"mcp": {"server": {"enabled": True}}})
        data = json.loads(path.read_text())
        assert data["mcp"]["server"]["enabled"] is True


class TestFindContextEntries:
    """Tests for finding existing context-mcp entries in configs."""

    def test_find_in_opencode(self):
        """Finds context entries in opencode format."""
        config = {
            "mcp": {
                "context": {"command": ["uv", "run", "context-mcp"]},
                "other": {"command": ["npx", "other-server"]},
            }
        }
        entries = _find_context_entries(config, "opencode")
        assert "context" in entries
        assert "other" not in entries

    def test_find_in_cursor(self):
        """Finds context entries in cursor format."""
        config = {
            "mcpServers": {
                "context": {"command": "uv", "args": ["run", "context-mcp"]},
                "other": {"command": "npx", "args": ["other-server"]},
            }
        }
        entries = _find_context_entries(config, "cursor")
        assert "context" in entries
        assert "other" not in entries

    def test_find_in_claude(self):
        """Finds context entries in claude format."""
        config = {
            "mcpServers": {
                "context": {"command": "uv", "args": ["run", "context-mcp"]},
            }
        }
        entries = _find_context_entries(config, "claude")
        assert "context" in entries

    def test_find_empty_config(self):
        """Empty config returns no entries."""
        assert _find_context_entries({}, "opencode") == {}
        assert _find_context_entries({}, "cursor") == {}


class TestIsContextEntry:
    """Tests for context entry detection."""

    def test_opencode_match(self):
        entry = {"command": ["uv", "--directory", "/x", "run", "context-mcp"]}
        assert _is_context_entry(entry, "opencode") is True

    def test_opencode_no_match(self):
        entry = {"command": ["npx", "other-server"]}
        assert _is_context_entry(entry, "opencode") is False

    def test_cursor_match_command(self):
        entry = {"command": "context-mcp", "args": []}
        assert _is_context_entry(entry, "cursor") is True

    def test_cursor_match_args(self):
        entry = {"command": "uv", "args": ["run", "context-mcp"]}
        assert _is_context_entry(entry, "cursor") is True

    def test_cursor_no_match(self):
        entry = {"command": "npx", "args": ["other"]}
        assert _is_context_entry(entry, "cursor") is False


class TestEntryBuilders:
    """Tests for config entry builders."""

    def test_opencode_entry(self, temp_project_dir: Path):
        """Builds opencode-format entry from source path."""
        entry = _build_opencode_entry(Path("/ctx"), temp_project_dir)
        assert entry["type"] == "local"
        assert "context-mcp" in entry["command"]
        assert entry["cwd"] == "."
        assert entry["enabled"] is True

    def test_opencode_entry_global(self, temp_project_dir: Path):
        """Builds opencode-format entry for global install."""
        entry = _build_opencode_entry(None, temp_project_dir)
        assert entry["type"] == "local"
        assert entry["command"] == ["devmcp-context"]
        assert entry["cwd"] == "."
        assert entry["enabled"] is True

    def test_cursor_entry(self, temp_project_dir: Path):
        """Builds cursor-format entry from source path."""
        entry = _build_cursor_entry(Path("/ctx"), temp_project_dir)
        assert entry["command"] == "uv"
        assert any("context-mcp" in a for a in entry["args"])

    def test_cursor_entry_global(self, temp_project_dir: Path):
        """Builds cursor-format entry for global install."""
        entry = _build_cursor_entry(None, temp_project_dir)
        assert entry["command"] == "devmcp-context"
        assert entry["args"] == []

    def test_claude_entry(self, temp_project_dir: Path):
        """Builds claude-format entry from source path."""
        entry = _build_claude_entry(Path("/ctx"), temp_project_dir)
        assert entry["command"] == "uv"
        assert any("context-mcp" in a for a in entry["args"])
        assert entry["env"]["CONTEXT_MCP_PROJECT_ROOT"] == str(temp_project_dir)

    def test_claude_entry_global(self, temp_project_dir: Path):
        """Builds claude-format entry for global install."""
        entry = _build_claude_entry(None, temp_project_dir)
        assert entry["command"] == "devmcp-context"
        assert entry["args"] == []
        assert entry["env"]["CONTEXT_MCP_PROJECT_ROOT"] == str(temp_project_dir)


class TestEntryNameGeneration:
    """Tests for entry name generation."""

    def test_basic_name(self, temp_project_dir: Path):
        """Uses directory name for basic entry name."""
        name = _entry_name_for_project(temp_project_dir, set())
        assert name.startswith("context-")

    def test_avoids_collision(self, temp_project_dir: Path):
        """Appends number when name is taken."""
        name = _entry_name_for_project(temp_project_dir, {"context-" + temp_project_dir.name})
        assert name.endswith("-2")

    def test_custom_name(self):
        """Custom name is used as-is."""
        # This is tested via run_init, not directly


class TestGetConfigPath:
    """Tests for config path resolution."""

    def test_opencode_path(self, temp_project_dir: Path):
        path = _get_config_path("opencode", temp_project_dir)
        assert path == temp_project_dir / "opencode.json"

    def test_cursor_path(self, temp_project_dir: Path):
        path = _get_config_path("cursor", temp_project_dir)
        assert path == temp_project_dir / ".cursor" / "mcp.json"


class TestGenericSnippet:
    """Tests for generic config snippet generation."""

    def test_snippet_contains_path(self, temp_project_dir: Path):
        snippet = _generate_generic_snippet(Path("/ctx"), temp_project_dir)
        assert "/ctx" in snippet
        assert "context-mcp" in snippet

    def test_snippet_global_install(self, temp_project_dir: Path):
        snippet = _generate_generic_snippet(None, temp_project_dir)
        assert "devmcp-context" in snippet
        assert "uv" not in snippet


class TestRunInit:
    """Tests for the full init flow."""

    def test_init_scaffolds(self, temp_project_dir: Path):
        """Init creates ai-context/ directory."""
        result = run_init(temp_project_dir, client="opencode")
        assert (temp_project_dir / "ai-context").exists()
        assert "Created" in result or "already exists" in result

    def test_init_writes_opencode_config(self, temp_project_dir: Path):
        """Init writes opencode.json with MCP entry."""
        run_init(temp_project_dir, client="opencode")
        config = json.loads((temp_project_dir / "opencode.json").read_text())
        assert "mcp" in config
        assert len(config["mcp"]) == 1
        entry = next(iter(config["mcp"].values()))
        assert entry["type"] == "local"

    def test_init_writes_cursor_config(self, temp_project_dir: Path):
        """Init writes .cursor/mcp.json with MCP entry."""
        run_init(temp_project_dir, client="cursor")
        config = json.loads((temp_project_dir / ".cursor" / "mcp.json").read_text())
        assert "mcpServers" in config
        assert len(config["mcpServers"]) == 1

    def test_init_skips_existing(self, temp_project_dir: Path):
        """Init skips if entry already points to same project."""
        run_init(temp_project_dir, client="opencode")
        result = run_init(temp_project_dir, client="opencode")
        assert "Already configured" in result

    def test_init_multi_project(self, temp_project_dir: Path):
        """Init adds second entry with different name when first points elsewhere."""
        # Create a config with an entry that points to a different project
        config = {
            "mcp": {
                "context-other": {
                    "type": "local",
                    "command": ["uv", "run", "context-mcp"],
                    "cwd": "/other/project",
                }
            }
        }
        (temp_project_dir / "opencode.json").write_text(json.dumps(config, indent=2))

        run_init(temp_project_dir, client="opencode")
        config = json.loads((temp_project_dir / "opencode.json").read_text())
        assert "context-other" in config["mcp"]
        # Should have added a second entry
        assert len(config["mcp"]) == 2

    def test_init_custom_name(self, temp_project_dir: Path):
        """Init uses custom name when provided."""
        run_init(temp_project_dir, client="opencode", name="my-context")
        config = json.loads((temp_project_dir / "opencode.json").read_text())
        assert "my-context" in config["mcp"]

    def test_init_claude_writes_env(self, temp_project_dir: Path):
        """Init for Claude includes CONTEXT_MCP_PROJECT_ROOT env var."""
        # We can't test actual Claude config path, but we can test the builder
        entry = _build_claude_entry(Path("/ctx"), temp_project_dir)
        assert "CONTEXT_MCP_PROJECT_ROOT" in entry["env"]
        assert entry["env"]["CONTEXT_MCP_PROJECT_ROOT"] == str(temp_project_dir)
