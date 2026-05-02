from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .models import Category, ContextEntry
from .scaffold import scaffold
from .storage import (
    delete_entry,
    get_all_summaries,
    load_category,
    purge_expired,
    save_entry,
    search_all,
)

mcp = FastMCP(
    "context-mcp",
    instructions=(
        "Use these tools to read and write structured project memory. "
        "Always call context_status at session start to understand what you already know. "
        "Save anything worth remembering across sessions via context_save. "
        "Prefer targeted context_load(category=...) over loading everything at once."
    ),
)


def _get_project_root() -> Path:
    """Resolve project root from env var or cwd."""
    root = os.environ.get("CONTEXT_MCP_PROJECT_ROOT")
    path = Path(root) if root else Path.cwd()
    scaffold(path)
    return path


# Tools :)
@mcp.tool()
def context_status() -> dict:
    """
    Get a summary of all context categories — entry counts, staleness, descriptions.
    Call this at the start of every session to understand what you already know.
    """
    root = _get_project_root()
    summaries = get_all_summaries(root)
    return {
        "project_root": str(root),
        "categories": summaries,
        "tip": "Call context_load(category=...) to read entries from a specific category.",
    }


@mcp.tool()
def context_load(category: str, include_expired: bool = False) -> dict:
    """
    Load all entries from a category.

    Args:
        category: One of: project, decisions, errors, tasks, ephemeral
        include_expired: If True, include expired entries (default False)
    """
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
) -> dict:
    """
    Save or update a context entry.

    Args:
        category: One of: project, decisions, errors, tasks, ephemeral
        key: Short unique identifier e.g. "auth-strategy" or "bug-login-redirect"
        value: The content to remember. Be specific and concise.
        tags: Optional list of tags for search e.g. ["auth", "security"]
        ttl_days: Override default TTL. None = use category default.
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
    )

    save_entry(root, entry)

    return {
        "saved": True,
        "category": category,
        "key": key,
        "ttl_days": entry.ttl_days,
        "expires": "never" if entry.ttl_days is None else f"in {entry.ttl_days} days",
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
        "message": "Entry removed." if deleted else "Key not found — nothing deleted.",
    }


@mcp.tool()
def context_search(query: str) -> dict:
    """
    Search across all categories by keyword.
    Matches against entry keys, values, and tags.

    Args:
        query: Search term (case-insensitive)
    """
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="context-mcp",
        description="Structured AI memory MCP server.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="context-mcp v0.1.0",
    )
    # Parse known args to support --help/--version without starting the server.
    parser.parse_known_args()
    _get_project_root()
    mcp.run()


if __name__ == "__main__":
    main()
