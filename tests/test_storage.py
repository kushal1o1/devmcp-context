"""Tests for context_mcp.storage module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from context_mcp.models import Category, ContextEntry
from context_mcp.storage import (
    delete_entry,
    get_all_summaries,
    load_category,
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
