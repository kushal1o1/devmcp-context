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
    ttl_days: int | None = Field(None, description="Days until expiry. None = never.")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="agent", description="Who wrote this: agent | human")

    @model_validator(mode="before")
    @classmethod
    def set_default_ttl(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("ttl_days") is None:
            cat = data.get("category")
            if cat:
                category = Category(cat) if isinstance(cat, str) else cat
                data["ttl_days"] = DEFAULT_TTL_DAYS.get(category)
        return data

    @property
    def is_expired(self) -> bool:
        if self.ttl_days is None:
            return False
        expiry = self.updated_at + timedelta(days=self.ttl_days)
        return datetime.now(UTC) > expiry

    @property
    def age_days(self) -> int:
        delta = datetime.now(UTC) - self.updated_at
        return delta.days

    def to_md_block(self) -> str:
        """Render entry as a markdown block with YAML frontmatter-style header."""
        tags_str = ", ".join(self.tags) if self.tags else ""
        ttl_str = f"{self.ttl_days}d" if self.ttl_days else "never"
        lines = [
            f"### {self.key}",
            f"<!-- meta: created={self.created_at.isoformat()} updated={self.updated_at.isoformat()} ttl={ttl_str} source={self.source} tags={tags_str} -->",
            "",
            self.value,
            "",
        ]
        return "\n".join(lines)


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
