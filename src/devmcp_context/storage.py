from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    CATEGORY_DESCRIPTIONS,
    Category,
    CategoryFile,
    ContextEntry,
    lead_fact,
)

FOLDER_NAME = "ai-context"
SESSION_LOG_FILE = "_session_log.md"

# Match the entire meta comment content, then parse key=value pairs from it.
META_PATTERN = re.compile(r"<!-- meta: (.*?) -->", re.DOTALL)
_KV_PATTERN = re.compile(r"(\w+)=(\S*)")


def _parse_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _parse_ttl(value: str) -> int | None:
    if value == "never":
        return None
    return int(value.rstrip("d"))


def _parse_tags(value: str) -> list[str]:
    if not value.strip():
        return []
    return [t.strip() for t in value.split("|") if t.strip()]


def _parse_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _category_file_path(project_root: Path, category: Category) -> Path:
    return project_root / FOLDER_NAME / f"{category.value}.md"


def _meta_file_path(project_root: Path) -> Path:
    return project_root / FOLDER_NAME / "_meta.md"


def _session_log_path(project_root: Path) -> Path:
    return project_root / FOLDER_NAME / SESSION_LOG_FILE


def parse_category_file(path: Path, category: Category) -> CategoryFile:
    """Parse a markdown category file into a CategoryFile model."""
    if not path.exists():
        return CategoryFile(category=category)

    content = path.read_text(encoding="utf-8")
    entries: list[ContextEntry] = []

    # Split on ### headers as we store entries in separate blocks using this approach
    blocks = re.split(r"^### ", content, flags=re.MULTILINE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        key = lines[0].strip()
        rest = "\n".join(lines[1:]).strip()

        meta_match = META_PATTERN.search(rest)
        if not meta_match:
            continue

        value = META_PATTERN.sub("", rest).strip()
        meta_content = meta_match.group(1)

        # Parse key=value pairs from meta content
        m = {k: v.strip() for k, v in _KV_PATTERN.findall(meta_content)}

        entries.append(
            ContextEntry(
                key=key,
                value=value,
                category=category,
                created_at=_parse_datetime(m["created"]),
                updated_at=_parse_datetime(m["updated"]),
                ttl_days=_parse_ttl(m["ttl"]),
                source=m["source"],
                tags=_parse_tags(m.get("tags", "")),
                what_worked=_parse_optional(m.get("what_worked")),
                what_failed=_parse_optional(m.get("what_failed")),
                superseded_by=_parse_optional(m.get("superseded_by")),
            )
        )

    return CategoryFile(category=category, entries=entries)


def write_category_file(project_root: Path, category_file: CategoryFile) -> None:
    """Write a CategoryFile back to disk as markdown."""
    path = _category_file_path(project_root, category_file.category)
    path.parent.mkdir(parents=True, exist_ok=True)
    cat = category_file.category

    header = "\n".join(
        [
            f"# {cat.value}",
            "",
            f"> {CATEGORY_DESCRIPTIONS[cat]}",
            "",
            "---",
            "",
        ]
    )

    blocks = [header]
    for entry in category_file.entries:
        blocks.append(entry.to_md_block())

    path.write_text("\n".join(blocks), encoding="utf-8")


def load_category(project_root: Path, category: Category) -> CategoryFile:
    path = _category_file_path(project_root, category)
    return parse_category_file(path, category)


def _find_entry(project_root: Path, category: Category, key: str) -> ContextEntry | None:
    """Find a single entry by category and key."""
    cat_file = load_category(project_root, category)
    for e in cat_file.entries:
        if e.key == key:
            return e
    return None


def save_entry(
    project_root: Path,
    entry: ContextEntry,
    preserve_created_at: bool = True,
) -> None:
    """Upsert an entry into its category file.

    When preserve_created_at is True and an entry with the same key already exists,
    the original created_at is carried forward instead of being reset.
    """
    cat_file = load_category(project_root, entry.category)

    existing_keys = {e.key: i for i, e in enumerate(cat_file.entries)}
    if entry.key in existing_keys:
        existing = cat_file.entries[existing_keys[entry.key]]
        if preserve_created_at:
            entry = entry.model_copy(update={"created_at": existing.created_at})
        cat_file.entries[existing_keys[entry.key]] = entry
    else:
        cat_file.entries.append(entry)

    write_category_file(project_root, cat_file)


def delete_entry(project_root: Path, category: Category, key: str) -> bool:
    """Delete an entry by key. Returns True if found and deleted."""
    cat_file = load_category(project_root, category)
    before = len(cat_file.entries)
    cat_file.entries = [e for e in cat_file.entries if e.key != key]

    if len(cat_file.entries) == before:
        return False

    write_category_file(project_root, cat_file)
    return True


def _follow_superseded(
    project_root: Path, entry: ContextEntry, _depth: int = 0
) -> ContextEntry:
    """Follow superseded_by pointers to return the successor entry.

    Returns the current entry if not superseded or if the pointer chain is broken.
    Guards against infinite loops with a depth limit.
    """
    if entry.superseded_by is None or _depth > 10:
        return entry

    successor = _find_entry(project_root, entry.category, entry.superseded_by)
    if successor is None:
        return entry

    return _follow_superseded(project_root, successor, _depth + 1)


def search_all(project_root: Path, query: str) -> list[ContextEntry]:
    """Simple case-insensitive search across all active entries.

    Superseded entries are skipped — their successors are returned instead.
    """
    query_lower = query.lower()
    results: list[ContextEntry] = []

    for category in Category:
        cat_file = load_category(project_root, category)
        for entry in cat_file.active_entries:
            if entry.is_superseded:
                continue
            if (
                query_lower in entry.key.lower()
                or query_lower in entry.value.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

    return results


def purge_expired(project_root: Path) -> int:
    """Remove all expired entries across all categories. Returns count removed."""
    total_removed = 0

    for category in Category:
        cat_file = load_category(project_root, category)
        before = len(cat_file.entries)
        cat_file.entries = cat_file.active_entries
        removed = before - len(cat_file.entries)
        if removed > 0:
            write_category_file(project_root, cat_file)
            total_removed += removed

    return total_removed


def get_all_summaries(project_root: Path) -> list[dict]:
    """Return summary stats for all categories."""
    return [load_category(project_root, cat).summary() for cat in Category]


def get_session_index(project_root: Path) -> dict[str, list[dict]]:
    """Build a compact index of all categories with lead facts.

    Returns a dict mapping category names to lists of {key, lead_fact, superseded_by} dicts.
    """
    index: dict[str, list[dict]] = {}
    for category in Category:
        cat_file = load_category(project_root, category)
        entries = cat_file.active_entries
        index[category.value] = [
            {
                "key": e.key,
                "lead_fact": lead_fact(e),
                "superseded_by": e.superseded_by,
            }
            for e in entries
        ]
    return index


def log_session_start(project_root: Path, recall_fired: bool) -> None:
    """Append a session start metric to the session log."""
    log_path = _session_log_path(project_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    line = f"| {timestamp} | {str(recall_fired).lower()} |\n"

    if not log_path.exists():
        log_path.write_text(
            "# Session Log\n\n"
            "| Timestamp | Recall fired before first edit |\n"
            "|-----------|-------------------------------|\n",
            encoding="utf-8",
        )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def get_recent_session_stats(project_root: Path, n: int = 10) -> list[dict]:
    """Read the last N session log entries."""
    log_path = _session_log_path(project_root)
    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    # Skip header (3 lines: title, blank, table header, separator)
    data_lines = [line for line in lines[3:] if line.startswith("|")]

    results = []
    for line in data_lines[-n:]:
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 2:
            results.append(
                {"timestamp": parts[0], "recall_fired": parts[1] == "true"}
            )
    return results
