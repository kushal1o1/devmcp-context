"""Tests for devmcp_context.models module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from devmcp_context.models import Category, CategoryFile, ContextEntry


class TestCategory:
    """Tests for the Category enum."""

    def test_all_categories_exist(self):
        """Test that all expected categories are defined."""
        categories = list(Category)
        assert len(categories) == 5
        assert Category.project in categories
        assert Category.decisions in categories
        assert Category.errors in categories
        assert Category.tasks in categories
        assert Category.ephemeral in categories

    def test_category_values(self):
        """Test category string values."""
        assert Category.project.value == "project"
        assert Category.decisions.value == "decisions"
        assert Category.errors.value == "errors"
        assert Category.tasks.value == "tasks"
        assert Category.ephemeral.value == "ephemeral"


class TestContextEntry:
    """Tests for the ContextEntry model."""

    def test_create_minimal_entry(self):
        """Test creating an entry with minimal required fields."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            ttl_days=None,
        )
        assert entry.key == "test-key"
        assert entry.value == "test value"
        assert entry.category == Category.project
        assert entry.source == "agent"
        assert entry.tags == []
        assert entry.ttl_days is None  # project category default

    def test_create_entry_with_tags(self):
        """Test creating an entry with tags."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            tags=["tag1", "tag2"],
            ttl_days=None,
        )
        assert entry.tags == ["tag1", "tag2"]

    def test_default_ttl_assignment(self):
        """Test that default TTL is assigned based on category."""
        # Project and decisions should have None (never expire)
        project_entry = ContextEntry(key="key1", value="val1", category=Category.project)
        assert project_entry.ttl_days is None

        decisions_entry = ContextEntry(key="key1", value="val1", category=Category.decisions)
        assert decisions_entry.ttl_days is None

        # Errors should have 30 days
        errors_entry = ContextEntry(key="key1", value="val1", category=Category.errors)
        assert errors_entry.ttl_days == 30

        # Tasks should have 14 days
        tasks_entry = ContextEntry(key="key1", value="val1", category=Category.tasks)
        assert tasks_entry.ttl_days == 14

        # Ephemeral should have 1 day
        ephemeral_entry = ContextEntry(key="key1", value="val1", category=Category.ephemeral)
        assert ephemeral_entry.ttl_days == 1

    def test_custom_ttl(self):
        """Test setting a custom TTL."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            ttl_days=5,
        )
        assert entry.ttl_days == 5

    def test_is_expired_false(self):
        """Test that a recent entry is not expired."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.errors,  # 30 day TTL
            ttl_days=30,
        )
        assert entry.is_expired is False

    def test_is_expired_true(self):
        """Test that an old entry is expired."""
        past = datetime.now(UTC) - timedelta(days=40)
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.errors,
            ttl_days=30,
            created_at=past,
            updated_at=past,
        )
        assert entry.is_expired is True

    def test_is_expired_never(self):
        """Test that an entry with None TTL never expires."""
        past = datetime.now(UTC) - timedelta(days=1000)
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            ttl_days=None,
            created_at=past,
            updated_at=past,
        )
        assert entry.is_expired is False

    def test_age_days(self):
        """Test the age_days property."""
        past = datetime.now(UTC) - timedelta(days=5)
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            updated_at=past,
        )
        # Should be approximately 5 days old
        assert 4 <= entry.age_days <= 6

    def test_to_md_block(self):
        """Test markdown block generation."""
        entry = ContextEntry(
            key="test-key",
            value="test value",
            category=Category.project,
            ttl_days=None,
            tags=["tag1", "tag2"],
            source="test",
        )
        md = entry.to_md_block()
        assert "### test-key" in md
        assert "test value" in md
        assert "ttl=never" in md
        assert "tag1, tag2" in md
        assert "source=test" in md

    def test_to_md_block_with_ttl(self):
        """Test markdown block generation with TTL."""
        entry = ContextEntry(
            key="another-key",
            value="another value",
            category=Category.errors,
            ttl_days=30,
            tags=[],
            source="agent",
        )
        md = entry.to_md_block()
        assert "### another-key" in md
        assert "ttl=30d" in md


class TestCategoryFile:
    """Tests for the CategoryFile model."""

    def test_create_empty_category_file(self):
        """Test creating an empty category file."""
        cat_file = CategoryFile(category=Category.project)
        assert cat_file.category == Category.project
        assert cat_file.entries == []

    def test_create_category_file_with_entries(self):
        """Test creating a category file with entries."""
        entries = [
            ContextEntry(key="k1", value="v1", category=Category.project),
            ContextEntry(key="k2", value="v2", category=Category.project),
        ]
        cat_file = CategoryFile(category=Category.project, entries=entries)
        assert len(cat_file.entries) == 2

    def test_active_entries_filters_expired(self):
        """Test that active_entries filters out expired entries."""
        past = datetime.now(UTC) - timedelta(days=100)
        entries = [
            ContextEntry(
                key="active",
                value="v1",
                category=Category.errors,
                ttl_days=30,
            ),
            ContextEntry(
                key="expired",
                value="v2",
                category=Category.errors,
                ttl_days=30,
                updated_at=past,
            ),
        ]
        cat_file = CategoryFile(category=Category.errors, entries=entries)
        active = cat_file.active_entries
        assert len(active) == 1
        assert active[0].key == "active"

    def test_summary(self):
        """Test the summary method."""
        past = datetime.now(UTC) - timedelta(days=100)
        entries = [
            ContextEntry(
                key="active",
                value="v1",
                category=Category.errors,
                ttl_days=30,
            ),
            ContextEntry(
                key="expired",
                value="v2",
                category=Category.errors,
                ttl_days=30,
                updated_at=past,
            ),
        ]
        cat_file = CategoryFile(category=Category.errors, entries=entries)
        summary = cat_file.summary()
        assert summary["category"] == "errors"
        assert summary["total_entries"] == 2
        assert summary["active_entries"] == 1
        assert summary["expired_entries"] == 1
        assert "description" in summary
