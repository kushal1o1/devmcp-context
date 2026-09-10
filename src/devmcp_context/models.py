from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Category(StrEnum):
    project = "project"
    decisions = "decisions"
    errors = "errors"
    tasks = "tasks"
    ephemeral = "ephemeral"  # scratchpad temp data :)


DEFAULT_TTL_DAYS: dict[Category, int | None] = {
    Category.project: None,  # never expires
    Category.decisions: None,  # never expires
    Category.errors: 30,  # 30 days
    Category.tasks: 14,  # 14 days
    Category.ephemeral: 1,  # 1 day
}

CATEGORY_DESCRIPTIONS: dict[Category, str] = {
    Category.project: "Stack, goals, conventions, repo structure",
    Category.decisions: "Why X was chosen over Y — architectural choices",
    Category.errors: "Bugs seen, fixes tried, what worked",
    Category.tasks: "In progress, blocked, recently completed",
    Category.ephemeral: "Scratchpad — auto-expires in 1 day",
}


class ContextEntry(BaseModel):
    key: str = Field(..., description="Short unique identifier within category")
    value: str = Field(..., description="The actual content to remember")
    category: Category
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_days: int | None = Field(default=None, description="Days until expiry. None = never.")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="agent", description="Who wrote this: agent | human")
    what_worked: str | None = Field(
        default=None, description="What worked for this decision/error"
    )
    what_failed: str | None = Field(
        default=None, description="What failed for this decision/error"
    )
    superseded_by: str | None = Field(
        default=None,
        description="Key of the entry that supersedes this one. Recall follows the pointer.",
    )

    @model_validator(mode="before")
    @classmethod
    def set_default_ttl(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("ttl_days") is None:
            cat = data.get("category")
            if cat:
                category = Category(cat) if isinstance(cat, str) else cat
                data["ttl_days"] = DEFAULT_TTL_DAYS.get(category)
        return data

    @model_validator(mode="before")
    @classmethod
    def validate_outcome_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cat = data.get("category")
            if cat:
                category = Category(cat) if isinstance(cat, str) else cat
                has_outcomes = data.get("what_worked") or data.get("what_failed")
                if has_outcomes and category not in (Category.decisions, Category.errors):
                    raise ValueError(
                        f"what_worked/what_failed are only valid for decisions or errors, "
                        f"not {category.value}"
                    )
        return data

    @property
    def is_expired(self) -> bool:
        if self.ttl_days is None:
            return False
        expiry = self.updated_at + timedelta(days=self.ttl_days)
        return datetime.now(UTC) > expiry

    @property
    def is_superseded(self) -> bool:
        return self.superseded_by is not None

    @property
    def age_days(self) -> int:
        delta = datetime.now(UTC) - self.updated_at
        return delta.days

    def to_md_block(self) -> str:
        """Render entry as a markdown block with meta comment."""
        tags_str = TAG_DELIMITER.join(self.tags) if self.tags else ""
        ttl_str = f"{self.ttl_days}d" if self.ttl_days else "never"
        meta_parts = [
            f"created={self.created_at.isoformat()}",
            f"updated={self.updated_at.isoformat()}",
            f"ttl={ttl_str}",
            f"source={self.source}",
            f"tags={tags_str}",
        ]
        if self.what_worked:
            meta_parts.append(f"what_worked={self.what_worked}")
        if self.what_failed:
            meta_parts.append(f"what_failed={self.what_failed}")
        if self.superseded_by:
            meta_parts.append(f"superseded_by={self.superseded_by}")
        meta_str = " ".join(meta_parts)
        lines = [
            f"### {self.key}",
            f"<!-- meta: {meta_str} -->",
            "",
            self.value,
            "",
        ]
        return "\n".join(lines)


def lead_fact(entry: ContextEntry) -> str:
    """Extract the lead fact from an entry's value — the first non-empty line."""
    for line in entry.value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return entry.value[:80]


class CategoryFile(BaseModel):
    category: Category
    entries: list[ContextEntry] = Field(default_factory=list)

    @property
    def active_entries(self) -> list[ContextEntry]:
        return [e for e in self.entries if not e.is_expired]

    def summary(self) -> dict[str, Any]:
        active = self.active_entries
        return {
            "category": self.category.value,
            "description": CATEGORY_DESCRIPTIONS[self.category],
            "total_entries": len(self.entries),
            "active_entries": len(active),
            "expired_entries": len(self.entries) - len(active),
            "oldest_days": max((e.age_days for e in active), default=0),
        }


# Tag delimiter: | (pipe) instead of , to avoid space ambiguity in meta comments.
TAG_DELIMITER = "|"
