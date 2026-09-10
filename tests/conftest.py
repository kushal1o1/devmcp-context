"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from devmcp_context.models import Category, ContextEntry


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_entry() -> ContextEntry:
    """Create a sample context entry for testing."""
    return ContextEntry(
        key="test-entry",
        value="This is a test entry",
        category=Category.project,
        tags=["test", "sample"],
        source="test",
        ttl_days=30,
    )


@pytest.fixture
def expired_entry() -> ContextEntry:
    """Create an expired entry for testing."""
    past_time = datetime.now(UTC) - timedelta(days=100)
    return ContextEntry(
        key="expired-entry",
        value="This entry is expired",
        category=Category.errors,
        created_at=past_time,
        updated_at=past_time,
        ttl_days=30,
        source="test",
    )


@pytest.fixture
def active_entry() -> ContextEntry:
    """Create an active (non-expired) entry for testing."""
    return ContextEntry(
        key="active-entry",
        value="This entry is still active",
        category=Category.tasks,
        ttl_days=14,
        tags=["urgent"],
        source="test",
    )


@pytest.fixture
def decision_entry() -> ContextEntry:
    """Create a decision entry with outcome fields for testing."""
    return ContextEntry(
        key="auth-decision",
        value="Chose JWT over sessions for statelessness",
        category=Category.decisions,
        what_worked="Zero server-side state, scales horizontally",
        what_failed="Token refresh is complex",
        source="test",
    )


@pytest.fixture
def superseded_entry() -> ContextEntry:
    """Create a superseded entry for testing."""
    return ContextEntry(
        key="old-auth-strategy",
        value="Used cookie-based sessions",
        category=Category.decisions,
        superseded_by="new-auth-strategy",
        source="test",
    )


@pytest.fixture
def successor_entry() -> ContextEntry:
    """Create a successor entry for testing."""
    return ContextEntry(
        key="new-auth-strategy",
        value="Switched to JWT tokens for stateless auth",
        category=Category.decisions,
        source="test",
    )
