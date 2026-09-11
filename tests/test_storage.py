"""Tests for devmcp_context.storage module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from devmcp_context.models import Category, ContextEntry
from devmcp_context.storage import (
    delete_entry,
    get_all_summaries,
    get_recent_session_stats,
    get_session_index,
    load_category,
    log_session_start,
    parse_category_file,
    purge_expired,
    save_entry,
    search_all,
)


class TestStorageFunctions:
    """Tests for storage module functions."""

    def test_save_and_load_entry(self, temp_project_dir: Path):
        """Test saving and loading an entry."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            tags=["tag1"],
        )
        save_entry(temp_project_dir, entry)

        # Load and verify
        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 1
        assert cat_file.entries[0].key == "test-key"
        assert cat_file.entries[0].value == "test value"
        assert cat_file.entries[0].tags == ["tag1"]

    def test_save_entry_creates_directory(self, temp_project_dir: Path):
        """Test that save_entry creates the ai-context directory."""
        entry = ContextEntry(
            key="key1",
            value="value1",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry)
        assert (temp_project_dir / "ai-context").exists()
        assert (temp_project_dir / "ai-context" / "project.md").exists()

    def test_update_existing_entry(self, temp_project_dir: Path):
        """Test updating an existing entry."""
        entry1 = ContextEntry(
            key="key1",
            value="value1",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry1)

        entry2 = ContextEntry(
            key="key1",
            value="updated value",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry2)

        # Should only have one entry
        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 1
        assert cat_file.entries[0].value == "updated value"

    def test_save_preserves_created_at(self, temp_project_dir: Path):
        """Test that updating an entry preserves its original created_at."""
        past = datetime.now(UTC) - timedelta(days=30)
        entry1 = ContextEntry(
            key="key1",
            value="value1",
            category=Category.project,
            created_at=past,
        )
        save_entry(temp_project_dir, entry1)

        entry2 = ContextEntry(
            key="key1",
            value="updated value",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry2, preserve_created_at=True)

        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 1
        # created_at should be preserved from the original
        assert cat_file.entries[0].created_at.date() == past.date()

    def test_save_does_not_preserve_created_at_when_disabled(self, temp_project_dir: Path):
        """Test that created_at is not preserved when preserve_created_at=False."""
        past = datetime.now(UTC) - timedelta(days=30)
        entry1 = ContextEntry(
            key="key1",
            value="value1",
            category=Category.project,
            created_at=past,
        )
        save_entry(temp_project_dir, entry1)

        entry2 = ContextEntry(
            key="key1",
            value="updated value",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry2, preserve_created_at=False)

        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 1
        # created_at should NOT be the old date (it gets the default from model)
        assert cat_file.entries[0].created_at.date() == datetime.now(UTC).date()

    def test_save_multiple_entries_different_categories(self, temp_project_dir: Path):
        """Test saving entries to different categories."""
        entry1 = ContextEntry(
            key="proj-key",
            value="project value",
            category=Category.project,
        )
        entry2 = ContextEntry(
            key="task-key",
            value="task value",
            category=Category.tasks,
        )
        save_entry(temp_project_dir, entry1)
        save_entry(temp_project_dir, entry2)

        proj_file = load_category(temp_project_dir, Category.project)
        task_file = load_category(temp_project_dir, Category.tasks)

        assert len(proj_file.entries) == 1
        assert len(task_file.entries) == 1

    def test_delete_entry_success(self, temp_project_dir: Path):
        """Test successfully deleting an entry."""
        entry = ContextEntry(
            key="key-to-delete",
            value="will be deleted",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry)

        # Verify it exists
        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 1

        # Delete it
        result = delete_entry(temp_project_dir, Category.project, "key-to-delete")
        assert result is True

        # Verify it's gone
        cat_file = load_category(temp_project_dir, Category.project)
        assert len(cat_file.entries) == 0

    def test_delete_entry_not_found(self, temp_project_dir: Path):
        """Test deleting a non-existent entry returns False."""
        result = delete_entry(temp_project_dir, Category.project, "non-existent")
        assert result is False

    def test_search_by_key(self, temp_project_dir: Path):
        """Test searching entries by key."""
        entry = ContextEntry(
            key="auth-strategy",
            value="Using OAuth2",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry)

        results = search_all(temp_project_dir, "auth")
        assert len(results) == 1
        assert results[0].key == "auth-strategy"

    def test_search_by_value(self, temp_project_dir: Path):
        """Test searching entries by value."""
        entry = ContextEntry(
            key="config",
            value="Database connection string",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry)

        results = search_all(temp_project_dir, "database")
        assert len(results) == 1

    def test_search_by_tag(self, temp_project_dir: Path):
        """Test searching entries by tag."""
        entry = ContextEntry(
            key="key1",
            value="some value",
            category=Category.project,
            tags=["important", "urgent"],
        )
        save_entry(temp_project_dir, entry)

        results = search_all(temp_project_dir, "urgent")
        assert len(results) == 1

    def test_search_case_insensitive(self, temp_project_dir: Path):
        """Test that search is case-insensitive."""
        entry = ContextEntry(
            key="MyKey",
            value="MyValue",
            category=Category.project,
            tags=["MyTag"],
        )
        save_entry(temp_project_dir, entry)

        results_key = search_all(temp_project_dir, "mykey")
        results_value = search_all(temp_project_dir, "myvalue")
        results_tag = search_all(temp_project_dir, "mytag")

        assert len(results_key) == 1
        assert len(results_value) == 1
        assert len(results_tag) == 1

    def test_search_no_results(self, temp_project_dir: Path):
        """Test search that returns no results."""
        entry = ContextEntry(
            key="key1",
            value="value1",
            category=Category.project,
        )
        save_entry(temp_project_dir, entry)

        results = search_all(temp_project_dir, "nonexistent")
        assert len(results) == 0

    def test_search_excludes_expired(self, temp_project_dir: Path):
        """Test that search excludes expired entries."""
        past = datetime.now(UTC) - timedelta(days=100)
        entry = ContextEntry(
            key="old-entry",
            value="This is old",
            category=Category.errors,
            ttl_days=30,
            updated_at=past,
        )
        save_entry(temp_project_dir, entry)

        results = search_all(temp_project_dir, "old")
        assert len(results) == 0

    def test_search_excludes_superseded(self, temp_project_dir: Path):
        """Test that search excludes superseded entries."""
        old_entry = ContextEntry(
            key="old-auth",
            value="cookie-based sessions",
            category=Category.decisions,
            ttl_days=None,
            superseded_by="new-auth",
        )
        new_entry = ContextEntry(
            key="new-auth",
            value="JWT tokens for stateless auth",
            category=Category.decisions,
            ttl_days=None,
        )
        save_entry(temp_project_dir, old_entry)
        save_entry(temp_project_dir, new_entry)

        # Searching for the old value should NOT return the superseded entry
        results = search_all(temp_project_dir, "cookie")
        assert len(results) == 0

        # Searching for the new value should return it
        results = search_all(temp_project_dir, "JWT")
        assert len(results) == 1
        assert results[0].key == "new-auth"

    def test_purge_expired(self, temp_project_dir: Path):
        """Test purging expired entries."""
        past = datetime.now(UTC) - timedelta(days=100)

        # Active entry
        entry1 = ContextEntry(
            key="active",
            value="Still valid",
            category=Category.errors,
            ttl_days=30,
        )
        # Expired entry
        entry2 = ContextEntry(
            key="expired",
            value="Too old",
            category=Category.errors,
            ttl_days=30,
            updated_at=past,
        )
        save_entry(temp_project_dir, entry1)
        save_entry(temp_project_dir, entry2)

        # Verify both exist
        cat_file = load_category(temp_project_dir, Category.errors)
        assert len(cat_file.entries) == 2

        # Purge
        removed = purge_expired(temp_project_dir)
        assert removed == 1

        # Verify only active remains
        cat_file = load_category(temp_project_dir, Category.errors)
        assert len(cat_file.entries) == 1
        assert cat_file.entries[0].key == "active"

    def test_purge_expired_multiple_categories(self, temp_project_dir: Path):
        """Test purging expired entries across multiple categories."""
        past = datetime.now(UTC) - timedelta(days=100)

        entry1 = ContextEntry(
            key="old-error",
            value="Old",
            category=Category.errors,
            ttl_days=30,
            updated_at=past,
        )
        entry2 = ContextEntry(
            key="old-task",
            value="Old",
            category=Category.tasks,
            ttl_days=14,
            updated_at=past,
        )
        save_entry(temp_project_dir, entry1)
        save_entry(temp_project_dir, entry2)

        removed = purge_expired(temp_project_dir)
        assert removed == 2

    def test_get_all_summaries(self, temp_project_dir: Path):
        """Test getting summaries for all categories."""
        entry1 = ContextEntry(
            key="proj",
            value="value",
            category=Category.project,
        )
        entry2 = ContextEntry(
            key="task",
            value="value",
            category=Category.tasks,
        )
        save_entry(temp_project_dir, entry1)
        save_entry(temp_project_dir, entry2)

        summaries = get_all_summaries(temp_project_dir)
        assert len(summaries) == 5  # One for each category

        # Find and verify our entries
        proj_summary = next(s for s in summaries if s["category"] == "project")
        task_summary = next(s for s in summaries if s["category"] == "tasks")

        assert proj_summary["active_entries"] == 1
        assert task_summary["active_entries"] == 1


class TestParsingAndWriting:
    """Tests for parsing and writing category files."""

    def test_parse_empty_file(self, temp_project_dir: Path):
        """Test parsing a non-existent file."""
        path = temp_project_dir / "ai-context" / "project.md"
        cat_file = parse_category_file(path, Category.project)
        assert len(cat_file.entries) == 0

    def test_write_and_parse_roundtrip(self, temp_project_dir: Path):
        """Test that written entries can be parsed back correctly."""
        entry = ContextEntry(
            key="test",
            value="test value",
            category=Category.project,
            tags=["t1", "t2"],
            source="test",
        )
        save_entry(temp_project_dir, entry)

        # Parse the written file
        path = temp_project_dir / "ai-context" / "project.md"
        cat_file = parse_category_file(path, Category.project)

        assert len(cat_file.entries) == 1
        parsed = cat_file.entries[0]
        assert parsed.key == entry.key
        assert parsed.value == entry.value
        assert parsed.tags == ["t1", "t2"]
        assert parsed.source == "test"

    def test_write_and_parse_roundtrip_with_outcomes(self, temp_project_dir: Path):
        """Test roundtrip for entries with outcome fields."""
        entry = ContextEntry(
            key="decided",
            value="Chose X",
            category=Category.decisions,
            ttl_days=None,
            what_worked="Fast",
            what_failed="Complex",
        )
        save_entry(temp_project_dir, entry)

        path = temp_project_dir / "ai-context" / "decisions.md"
        cat_file = parse_category_file(path, Category.decisions)

        assert len(cat_file.entries) == 1
        parsed = cat_file.entries[0]
        assert parsed.what_worked == "Fast"
        assert parsed.what_failed == "Complex"

    def test_write_and_parse_roundtrip_superseded(self, temp_project_dir: Path):
        """Test roundtrip for superseded entries."""
        entry = ContextEntry(
            key="old",
            value="Old approach",
            category=Category.decisions,
            ttl_days=None,
            superseded_by="new",
        )
        save_entry(temp_project_dir, entry)

        path = temp_project_dir / "ai-context" / "decisions.md"
        cat_file = parse_category_file(path, Category.decisions)

        assert len(cat_file.entries) == 1
        parsed = cat_file.entries[0]
        assert parsed.superseded_by == "new"

    def test_write_includes_expired_entries(self, temp_project_dir: Path):
        """Test that write_category_file includes even expired entries (purge_expired removes them)."""
        past = datetime.now(UTC) - timedelta(days=100)
        entry1 = ContextEntry(
            key="active",
            value="Active",
            category=Category.errors,
            ttl_days=30,
        )
        entry2 = ContextEntry(
            key="expired",
            value="Expired",
            category=Category.errors,
            ttl_days=30,
            updated_at=past,
        )
        save_entry(temp_project_dir, entry1)
        save_entry(temp_project_dir, entry2)

        # The file should contain both entries
        path = temp_project_dir / "ai-context" / "errors.md"
        content = path.read_text()
        assert "active" in content
        assert "expired" in content


class TestSessionIndex:
    """Tests for the session index feature."""

    def test_get_session_index_empty(self, temp_project_dir: Path):
        """Test session index with no entries."""
        index = get_session_index(temp_project_dir)
        assert isinstance(index, dict)
        assert all(len(v) == 0 for v in index.values())

    def test_get_session_index_with_entries(self, temp_project_dir: Path):
        """Test session index returns lead facts."""
        entry = ContextEntry(
            key="db-host",
            value="localhost:5432 is the primary DB\nConnection pooling via PgBouncer",
            category=Category.project,
            ttl_days=None,
        )
        save_entry(temp_project_dir, entry)

        index = get_session_index(temp_project_dir)
        assert "project" in index
        assert len(index["project"]) == 1
        assert index["project"][0]["key"] == "db-host"
        assert index["project"][0]["lead_fact"] == "localhost:5432 is the primary DB"

    def test_get_session_index_superseded_shows_pointer(self, temp_project_dir: Path):
        """Test that superseded entries show their pointer in the index."""
        old = ContextEntry(
            key="old",
            value="Old value",
            category=Category.decisions,
            ttl_days=None,
            superseded_by="new",
        )
        new = ContextEntry(
            key="new",
            value="New value",
            category=Category.decisions,
            ttl_days=None,
        )
        save_entry(temp_project_dir, old)
        save_entry(temp_project_dir, new)

        index = get_session_index(temp_project_dir)
        old_in_index = next(e for e in index["decisions"] if e["key"] == "old")
        assert old_in_index["superseded_by"] == "new"


class TestSessionMetric:
    """Tests for session metric logging."""

    def test_log_session_start_creates_file(self, temp_project_dir: Path):
        """Test that log_session_start creates the log file."""
        log_path = temp_project_dir / "ai-context" / "_session_log.md"
        assert not log_path.exists()

        log_session_start(temp_project_dir, recall_fired=True)

        assert log_path.exists()
        content = log_path.read_text()
        assert "true" in content

    def test_log_session_start_appends(self, temp_project_dir: Path):
        """Test that log_session_start appends to existing log."""
        log_session_start(temp_project_dir, recall_fired=True)
        log_session_start(temp_project_dir, recall_fired=False)

        content = (temp_project_dir / "ai-context" / "_session_log.md").read_text()
        # Filter out header lines (table header + separator)
        data_lines = [
            line for line in content.splitlines()
            if line.startswith("|") and "Timestamp" not in line and "---" not in line
        ]
        assert len(data_lines) == 2
        assert "true" in data_lines[0]
        assert "false" in data_lines[1]

    def test_get_recent_session_stats_empty(self, temp_project_dir: Path):
        """Test getting stats when no log exists."""
        stats = get_recent_session_stats(temp_project_dir)
        assert stats == []

    def test_get_recent_session_stats(self, temp_project_dir: Path):
        """Test reading recent session stats."""
        log_session_start(temp_project_dir, recall_fired=True)
        log_session_start(temp_project_dir, recall_fired=False)
        log_session_start(temp_project_dir, recall_fired=True)

        stats = get_recent_session_stats(temp_project_dir, n=2)
        assert len(stats) == 2
        assert stats[0]["recall_fired"] is False
        assert stats[1]["recall_fired"] is True
