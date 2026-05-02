from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from .models import CATEGORY_DESCRIPTIONS, Category, CategoryFile, ContextEntry

FOLDER_NAME = "ai-context"
META_PATTERN = re.compile(
    r"<!-- meta: created=(?P<created>[^\s]+) updated=(?P<updated>[^\s]+) "
    r"ttl=(?P<ttl>[^\s]+) source=(?P<source>[^\s]+) tags=(?P<tags>[^>]*) -->"
)


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
    return [t.strip() for t in value.split(",") if t.strip()]


def _category_file_path(project_root: Path, category: Category) -> Path:
    return project_root / FOLDER_NAME / f"{category.value}.md"


def _meta_file_path(project_root: Path) -> Path:
    return project_root / FOLDER_NAME / "_meta.md"


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
        m = meta_match.groupdict()

        entries.append(
            ContextEntry(
                key=key,
                value=value,
                category=category,
                created_at=_parse_datetime(m["created"]),
                updated_at=_parse_datetime(m["updated"]),
                ttl_days=_parse_ttl(m["ttl"]),
                source=m["source"],
                tags=_parse_tags(m["tags"]),
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


def save_entry(project_root: Path, entry: ContextEntry) -> None:
    """Upsert an entry into its category file."""
    cat_file = load_category(project_root, entry.category)

    # Replace existing entry with same key, or append
    existing_keys = {e.key: i for i, e in enumerate(cat_file.entries)}
    if entry.key in existing_keys:
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


def search_all(project_root: Path, query: str) -> list[ContextEntry]:
    """Simple case-insensitive search across all active entries."""
    query_lower = query.lower()
    results: list[ContextEntry] = []

    for category in Category:
        cat_file = load_category(project_root, category)
        for entry in cat_file.active_entries:
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
