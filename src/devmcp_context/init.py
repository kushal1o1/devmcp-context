"""CLI init command - scaffold + configure MCP client in one shot."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from .scaffold import scaffold
from .storage import FOLDER_NAME

# Known MCP clients and their config locations
CLIENTS = {
    "opencode": "opencode.json",
    "cursor": ".cursor/mcp.json",
}


def _detect_client(project_root: Path) -> str | None:
    """Auto-detect which MCP client is in use based on filesystem signals."""
    # Check for opencode config in project root
    if (project_root / "opencode.json").exists():
        return "opencode"
    if (project_root / "opencode.jsonc").exists():
        return "opencode"

    # Check for Cursor config in project root
    if (project_root / ".cursor" / "mcp.json").exists():
        return "cursor"

    # Check for Claude Desktop config
    claude_config = _claude_desktop_config_path()
    if claude_config and claude_config.exists():
        return "claude"

    return None


def _claude_desktop_config_path() -> Path | None:
    """Get the Claude Desktop config file path for the current platform."""
    system = platform.system()
    if system == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif system == "Windows":
        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "Claude" / "claude_desktop_config.json"
    else:
        # Linux - check common locations
        xdg_config = Path.home() / ".config"
        path = xdg_config / "Claude" / "claude_desktop_config.json"
        return path if path.exists() else None


def _resolve_context_mcp_path() -> Path | None:
    """Find the absolute path to the context-mcp source directory.

    Returns the repo root (with pyproject.toml) when running from source.
    Returns None when installed globally (pipx, pip) - use bare command instead.
    """
    # If running from source (uv/pip install -e), use the package location
    try:
        import devmcp_context

        package_dir = Path(devmcp_context.__file__).parent.parent.parent
        # Verify this looks like the context-mcp repo
        if (package_dir / "pyproject.toml").exists():
            return package_dir.resolve()
    except Exception:
        pass

    return None


def _find_context_entries(config: dict, client: str) -> dict[str, dict]:
    """Find existing context-mcp entries in a config dict.

    Returns a dict mapping entry name -> entry config for entries that look like
    context-mcp (command contains 'context-mcp' or 'devmcp-context').
    """
    entries: dict[str, dict] = {}

    if client == "opencode":
        mcp_section = config.get("mcp", {})
        for name, entry in mcp_section.items():
            if _is_context_entry(entry, client):
                entries[name] = entry
    elif client in ("cursor", "claude"):
        mcp_section = config.get("mcpServers", {})
        for name, entry in mcp_section.items():
            if _is_context_entry(entry, client):
                entries[name] = entry

    return entries


def _is_context_entry(entry: dict, client: str) -> bool:
    """Check if an MCP config entry looks like context-mcp."""
    if client == "opencode":
        cmd = entry.get("command", [])
        if isinstance(cmd, list):
            return any("context-mcp" in str(c) for c in cmd)
        return False
    else:
        # cursor / claude format
        cmd = entry.get("command", "")
        args = entry.get("args", [])
        if "context-mcp" in str(cmd) or "devmcp-context" in str(cmd):
            return True
        return any("context-mcp" in str(a) for a in args)


def _build_opencode_entry(context_mcp_path: Path | None, project_root: Path) -> dict:
    """Build an opencode-format MCP server entry."""
    if context_mcp_path is not None:
        return {
            "type": "local",
            "command": [
                "uv",
                "--directory",
                str(context_mcp_path),
                "run",
                "context-mcp",
            ],
            "cwd": ".",
            "enabled": True,
        }
    # Global install - use bare command
    return {
        "type": "local",
        "command": ["devmcp-context"],
        "cwd": ".",
        "enabled": True,
    }


def _build_cursor_entry(context_mcp_path: Path | None, project_root: Path) -> dict:
    """Build a Cursor-format MCP server entry."""
    if context_mcp_path is not None:
        return {
            "command": "uv",
            "args": [
                "--directory",
                str(context_mcp_path),
                "run",
                "context-mcp",
            ],
        }
    return {"command": "devmcp-context", "args": []}


def _build_claude_entry(context_mcp_path: Path | None, project_root: Path) -> dict:
    """Build a Claude Desktop-format MCP server entry."""
    if context_mcp_path is not None:
        return {
            "command": "uv",
            "args": [
                "--directory",
                str(context_mcp_path),
                "run",
                "context-mcp",
            ],
            "env": {
                "CONTEXT_MCP_PROJECT_ROOT": str(project_root),
            },
        }
    return {
        "command": "devmcp-context",
        "args": [],
        "env": {
            "CONTEXT_MCP_PROJECT_ROOT": str(project_root),
        },
    }


def _build_entry(client: str, context_mcp_path: Path | None, project_root: Path) -> dict:
    """Build the appropriate config entry for the given client."""
    if client == "opencode":
        return _build_opencode_entry(context_mcp_path, project_root)
    elif client == "cursor":
        return _build_cursor_entry(context_mcp_path, project_root)
    elif client == "claude":
        return _build_claude_entry(context_mcp_path, project_root)
    raise ValueError(f"Unknown client: {client}")


def _get_config_path(client: str, project_root: Path) -> Path | None:
    """Get the config file path for a given client."""
    if client == "opencode":
        return project_root / "opencode.json"
    elif client == "cursor":
        return project_root / ".cursor" / "mcp.json"
    elif client == "claude":
        return _claude_desktop_config_path()
    return None


def _read_config(path: Path) -> dict:
    """Read a JSON config file, returning empty dict if missing or empty."""
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def _write_config(path: Path, config: dict) -> None:
    """Write a JSON config file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _generate_generic_snippet(context_mcp_path: Path | None, project_root: Path) -> str:
    """Generate a generic config snippet for unknown clients."""
    if context_mcp_path is not None:
        return (
            "# Add this to your MCP client's config:\n"
            "#\n"
            '# For clients using the "command + args" format:\n'
            f"#   command: uv\n"
            f'#   args: ["--directory", "{context_mcp_path}", "run", "context-mcp"]\n'
            f"#\n"
            f'# For clients using the "command array" format:\n'
            f'#   command: ["uv", "--directory", "{context_mcp_path}", "run", "context-mcp"]\n'
            f"#\n"
            f"# The server will use {project_root} as the project root.\n"
            f"# If your client sets cwd to the project dir, no env var is needed.\n"
            f"# Otherwise, set CONTEXT_MCP_PROJECT_ROOT={project_root}"
        )
    return (
        "# Add this to your MCP client's config:\n"
        "#\n"
        "# command: devmcp-context\n"
        "#\n"
        f"# The server will use {project_root} as the project root.\n"
        "# If your client sets cwd to the project dir, no env var is needed.\n"
        f"# Otherwise, set CONTEXT_MCP_PROJECT_ROOT={project_root}"
    )


def _entry_name_for_project(project_root: Path, existing_names: set[str]) -> str:
    """Generate an entry name based on the project directory name."""
    base = f"context-{project_root.name}"
    if base not in existing_names:
        return base
    for i in range(2, 100):
        candidate = f"{base}-{i}"
        if candidate not in existing_names:
            return candidate
    return f"{base}-extra"


def run_init(
    project_root: Path,
    client: str | None = None,
    name: str | None = None,
) -> str:
    """Run the init command: scaffold + configure MCP client.

    Returns a summary message.
    """
    lines: list[str] = []

    # Step 1: Scaffold
    scaffolded = scaffold(project_root)
    if scaffolded:
        lines.append(f"Created {FOLDER_NAME}/ with category files.")
    else:
        lines.append(f"{FOLDER_NAME}/ already exists.")

    # Step 2: Find context-mcp path (None = global install via pipx/pip)
    context_mcp_path = _resolve_context_mcp_path()

    # Step 3: Detect client
    if client is None:
        client = _detect_client(project_root)

    if client is None:
        lines.append("")
        lines.append("No MCP client detected in this directory.")
        lines.append("Here's the config snippet to add manually:")
        lines.append("")
        lines.append(_generate_generic_snippet(context_mcp_path, project_root))
        return "\n".join(lines)

    lines.append(f"Detected client: {client}")

    # Step 4: Get or create config file
    config_path = _get_config_path(client, project_root)
    if config_path is None:
        lines.append(f"Could not determine config path for {client}.")
        return "\n".join(lines)

    config = _read_config(config_path)

    # Step 5: Find existing context entries
    existing = _find_context_entries(config, client)
    existing_names = set(existing.keys())

    # Check if this exact project root is already configured
    for entry_name, entry_config in existing.items():
        if _entry_points_to_project(entry_config, client, project_root):
            lines.append(f"Already configured: '{entry_name}' points to {project_root}")
            return "\n".join(lines)

    # Step 6: Determine entry name
    if name is None:
        name = _entry_name_for_project(project_root, existing_names)
    elif name in existing_names:
        lines.append(f"Entry name '{name}' already exists. Pick a different name.")
        return "\n".join(lines)

    # Step 7: Build and insert entry
    entry = _build_entry(client, context_mcp_path, project_root)

    if client == "opencode":
        config.setdefault("mcp", {})[name] = entry
    elif client in ("cursor", "claude"):
        config.setdefault("mcpServers", {})[name] = entry

    _write_config(config_path, config)

    lines.append(f"Updated {config_path}")
    lines.append(f"Added '{name}' MCP server entry for context-mcp.")

    if len(existing) > 0:
        lines.append(f"Existing context entries: {', '.join(existing_names)}")

    lines.append("")
    lines.append("Restart your MCP client to pick up the changes.")

    return "\n".join(lines)


def _entry_points_to_project(entry: dict, client: str, project_root: Path) -> bool:
    """Check if an MCP config entry points to the given project root."""
    project_str = str(project_root)

    if client == "opencode":
        # Check cwd field
        if entry.get("cwd") == project_str or entry.get("cwd") == ".":
            return True
        # Check env
        env = entry.get("environment", {})
        if env.get("CONTEXT_MCP_PROJECT_ROOT") == project_str:
            return True
    elif client in ("cursor", "claude"):
        env = entry.get("env", {})
        if env.get("CONTEXT_MCP_PROJECT_ROOT") == project_str:
            return True
        # Cursor with no env var uses cwd - hard to tell, assume not same
    return False
