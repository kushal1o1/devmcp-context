from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .models import Category, ContextEntry
from .scaffold import scaffold
from .storage import (
    delete_entry,
    get_all_summaries,
    get_recent_session_stats,
    get_session_index,
    load_category,
    log_session_start,
    purge_expired,
    save_entry,
    search_all,
)

mcp = FastMCP(
    "context-mcp",
    instructions=(
        "Use these tools to read and write structured project memory. "
        "IMPORTANT: Always call context_session_start at session start. "
        "It auto-loads project + decisions memory and shows a compact index "
        "of errors, tasks, and ephemeral entries. This is your recall - "
        "read it before acting on any task. "
        "Use context_load for full category details, context_search for targeted lookup. "
        "Save anything worth remembering across sessions via context_save. "
        "Put the key fact first in value fields - the first line is what gets shown in summaries."
    ),
)


def _get_project_root() -> Path:
    """Resolve project root from env var or cwd."""
    root = os.environ.get("CONTEXT_MCP_PROJECT_ROOT")
    path = Path(root) if root else Path.cwd()
    scaffold(path)
    return path


# Session-level state: tracks whether any recall tool was called
_session_recall_fired: bool = False
_session_recall_logged: bool = False


def _mark_recall_fired() -> None:
    global _session_recall_fired
    _session_recall_fired = True


def _maybe_log_session(root: Path) -> None:
    """Append a session metric row once per session (at first edit)."""
    global _session_recall_logged
    if not _session_recall_logged:
        log_session_start(root, recall_fired=_session_recall_fired)
        _session_recall_logged = True


# Tools :)
@mcp.tool()
def context_session_start() -> dict:
    """
    Start a session by loading memory. Call this FIRST, before any task.

    Returns:
    - Auto-loaded project and decisions entries (full content)
    - Compact index of errors, tasks, ephemeral (key + lead fact only)
    - Recent session recall stats (did recall fire before edits in past sessions?)
    """
    global _session_recall_fired, _session_recall_logged
    _session_recall_fired = False
    _session_recall_logged = False

    root = _get_project_root()

    # Auto-load project + decisions (always relevant, small)
    project_entries = load_category(root, Category.project).active_entries
    decisions_entries = load_category(root, Category.decisions).active_entries

    # Compact index for the rest
    index = get_session_index(root)

    # Recent session stats
    recent_stats = get_recent_session_stats(root, n=5)

    return {
        "project_root": str(root),
        "auto_loaded": {
            "project": [
                {"key": e.key, "value": e.value, "tags": e.tags}
                for e in project_entries
            ],
            "decisions": [
                {"key": e.key, "value": e.value, "tags": e.tags}
                for e in decisions_entries
            ],
        },
        "compact_index": {
            cat: entries
            for cat, entries in index.items()
            if cat not in ("project", "decisions")
        },
        "tip": (
            "Read the auto-loaded entries above. Use context_load(category=...) "
            "to read full entries from errors/tasks/ephemeral when needed. "
            "Use context_search(query=...) for targeted lookup."
        ),
        "recent_session_recall_stats": recent_stats,
    }


@mcp.tool()
def context_status() -> dict:
    """
    Get a summary of all context categories - entry counts, staleness, descriptions.
    Secondary to context_session_start; use this for quick status checks.
    """
    root = _get_project_root()
    summaries = get_all_summaries(root)
    return {
        "project_root": str(root),
        "categories": summaries,
        "tip": "Prefer context_session_start at session start for auto-loaded memory.",
    }


@mcp.tool()
def context_load(category: str, include_expired: bool = False) -> dict:
    """
    Load all entries from a category.

    Args:
        category: One of: project, decisions, errors, tasks, ephemeral
        include_expired: If True, include expired entries (default False)
    """
    global _session_recall_fired
    _session_recall_fired = True

    root = _get_project_root()

    try:
        cat = Category(category)
    except ValueError:
        valid = [c.value for c in Category]
        return {"error": f"Unknown category '{category}'. Valid: {valid}"}

    cat_file = load_category(root, cat)
    entries = cat_file.entries if include_expired else cat_file.active_entries

    return {
        "category": category,
        "entries": [
            {
                "key": e.key,
                "value": e.value,
                "age_days": e.age_days,
                "ttl_days": e.ttl_days,
                "tags": e.tags,
                "source": e.source,
                "what_worked": e.what_worked,
                "what_failed": e.what_failed,
                "superseded_by": e.superseded_by,
            }
            for e in entries
        ],
        "count": len(entries),
    }


@mcp.tool()
def context_save(
    category: str,
    key: str,
    value: str,
    tags: list[str] | None = None,
    ttl_days: int | None = None,
    what_worked: str | None = None,
    what_failed: str | None = None,
    superseded_by: str | None = None,
) -> dict:
    """
    Save or update a context entry.

    Args:
        category: One of: project, decisions, errors, tasks, ephemeral
        key: Short unique identifier e.g. "auth-strategy" or "bug-login-redirect"
        value: The content to remember. Put the key fact on the first line.
        tags: Optional list of tags for search e.g. ["auth", "security"]
        ttl_days: Override default TTL. None = use category default.
        what_worked: (decisions/errors only) What worked about this entry.
        what_failed: (decisions/errors only) What failed about this entry.
        superseded_by: Key of the entry that supersedes this one. The old entry stays
                       but recall will follow this pointer to the successor.
    """
    root = _get_project_root()

    try:
        cat = Category(category)
    except ValueError:
        valid = [c.value for c in Category]
        return {"error": f"Unknown category '{category}'. Valid: {valid}"}

    entry = ContextEntry(
        key=key,
        value=value,
        category=cat,
        tags=tags or [],
        ttl_days=ttl_days,
        source="agent",
        updated_at=datetime.now(UTC),
        what_worked=what_worked,
        what_failed=what_failed,
        superseded_by=superseded_by,
    )

    save_entry(root, entry, preserve_created_at=True)

    _maybe_log_session(root)

    return {
        "saved": True,
        "category": category,
        "key": key,
        "ttl_days": entry.ttl_days,
        "expires": "never" if entry.ttl_days is None else f"in {entry.ttl_days} days",
        "superseded_by": superseded_by,
    }


@mcp.tool()
def context_delete(category: str, key: str) -> dict:
    """
    Delete a specific entry from a category.

    Args:
        category: One of: project, decisions, errors, tasks, ephemeral
        key: The entry key to delete
    """
    root = _get_project_root()

    try:
        cat = Category(category)
    except ValueError:
        valid = [c.value for c in Category]
        return {"error": f"Unknown category '{category}'. Valid: {valid}"}

    deleted = delete_entry(root, cat, key)
    return {
        "deleted": deleted,
        "category": category,
        "key": key,
        "message": "Entry removed." if deleted else "Key not found - nothing deleted.",
    }


@mcp.tool()
def context_search(query: str) -> dict:
    """
    Search across all categories by keyword.
    Matches against entry keys, values, and tags.
    Superseded entries are excluded (their successors are returned instead).

    Args:
        query: Search term (case-insensitive)
    """
    global _session_recall_fired
    _session_recall_fired = True

    root = _get_project_root()
    results = search_all(root, query)

    return {
        "query": query,
        "results": [
            {
                "category": e.category.value,
                "key": e.key,
                "value": e.value,
                "age_days": e.age_days,
                "tags": e.tags,
                "what_worked": e.what_worked,
                "what_failed": e.what_failed,
            }
            for e in results
        ],
        "count": len(results),
    }


@mcp.tool()
def context_purge_expired() -> dict:
    """
    Remove all expired entries across all categories.
    Call this periodically to keep context lean and token-efficient.
    """
    root = _get_project_root()
    removed = purge_expired(root)
    return {
        "purged": removed,
        "message": f"Removed {removed} expired entries.",
    }


@mcp.tool()
def context_log_session_recall() -> dict:
    """
    Log whether recall fired before the first edit in this session.
    Usually called automatically at the first save - use this tool only
    when you want the metric for a session that made no edits.
    """
    global _session_recall_fired, _session_recall_logged
    root = _get_project_root()

    auto_logged = _session_recall_logged
    if not auto_logged:
        _maybe_log_session(root)

    recall_fired = _session_recall_fired
    if auto_logged:
        message = (
            "Session recall was already logged at first edit: "
            f"recall fired={'YES' if recall_fired else 'NO'}"
        )
    else:
        message = (
            "Session recall logged: "
            f"recall fired before first edit = {'YES' if recall_fired else 'NO'}"
        )

    return {
        "logged": True,
        "recall_fired": recall_fired,
        "message": message,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="devmcp-context",
        description="Structured AI memory MCP server.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="devmcp-context v0.2.0",
    )

    subparsers = parser.add_subparsers(dest="command")

    # init subcommand
    init_parser = subparsers.add_parser(
        "init",
        help="Scaffold ai-context/ and configure your MCP client.",
    )
    init_parser.add_argument(
        "--client",
        choices=["opencode", "cursor", "claude"],
        default=None,
        help="MCP client to configure (auto-detected if omitted).",
    )
    init_parser.add_argument(
        "--name",
        default=None,
        help="Custom name for the MCP server entry (default: auto-generated).",
    )
    init_parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project directory to initialize (default: current directory).",
    )

    args = parser.parse_args()

    if args.command == "init":
        from .init import run_init

        project_root = args.project_root or Path.cwd()
        result = run_init(
            project_root=project_root,
            client=args.client,
            name=args.name,
        )
        print(result)
        sys.exit(0)

    # Default: start the MCP server
    _get_project_root()
    mcp.run()


if __name__ == "__main__":
    main()
