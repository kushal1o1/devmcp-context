from __future__ import annotations

import json
from pathlib import Path

from .models import CATEGORY_DESCRIPTIONS, Category, ContextEntry
from .storage import FOLDER_NAME, _category_file_path, _meta_file_path, save_entry

GITIGNORE_NOTE = "# ai-context/ is intentionally tracked — it's your AI's memory\n"


def _detect_project_info(project_root: Path) -> dict[str, str]:
    """Minimal effort for the detection of project stack from common config files.:)"""
    info: dict[str, str] = {}

    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            info["name"] = data.get("name", "")
            deps = list(data.get("dependencies", {}).keys())[:6]
            info["stack"] = "Node.js / " + ", ".join(deps) if deps else "Node.js"
        except Exception:
            info["stack"] = "Node.js"

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        info["stack"] = "Python"
        if "fastapi" in content.lower():
            info["stack"] = "Python / FastAPI"
        elif "django" in content.lower():
            info["stack"] = "Python / Django"
        elif "flask" in content.lower():
            info["stack"] = "Python / Flask"

    if (project_root / "Cargo.toml").exists():
        info["stack"] = "Rust"
    if (project_root / "go.mod").exists():
        info["stack"] = "Go"

    readme = project_root / "README.md"
    if readme.exists():
        first_line = readme.read_text().splitlines()[0].lstrip("#").strip()
        if first_line:
            info["description"] = first_line

    # Just trying to detect ,cant cover all Its just for initial auto detection Not Accurate or Necessary at All

    return info


def _write_meta(project_root: Path) -> None:
    meta_path = _meta_file_path(project_root)
    meta_path.write_text(
        "# _meta\n\n"
        "> Auto-managed by context-mcp. Do not edit manually.\n\n"
        "This folder is your AI's structured memory for this project.\n\n"
        "## Categories\n\n"
        + "\n".join(f"- **{cat.value}** — {CATEGORY_DESCRIPTIONS[cat]}" for cat in Category)
        + "\n\n"
        "## How to use\n\n"
        "- Edit any `.md` file directly to add or fix entries\n"
        "- Delete an entry block to remove it\n"
        "- The agent will pick up your changes next session\n",
        encoding="utf-8",
    )


def scaffold(project_root: Path) -> bool:
    """
    Create the ai-context/ folder structure if it doesn't exist.
    Returns True if scaffolded fresh, False if already existed.
    """
    context_dir = project_root / FOLDER_NAME

    if context_dir.exists():
        return False

    context_dir.mkdir(parents=True)

    # Create empty category files
    for category in Category:
        path = _category_file_path(project_root, category)
        path.write_text(
            f"# {category.value}\n\n> {CATEGORY_DESCRIPTIONS[category]}\n\n---\n\n",
            encoding="utf-8",
        )

    # Seed project.md with auto-detected info :)
    project_info = _detect_project_info(project_root)

    if project_info.get("stack"):
        save_entry(
            project_root,
            ContextEntry(
                key="stack",
                value=project_info["stack"],
                category=Category.project,
                source="scaffold",
                ttl_days=None,
            ),
        )

    if project_info.get("name"):
        save_entry(
            project_root,
            ContextEntry(
                key="project-name",
                value=project_info["name"],
                category=Category.project,
                source="scaffold",
                ttl_days=None,
            ),
        )

    if project_info.get("description"):
        save_entry(
            project_root,
            ContextEntry(
                key="description",
                value=project_info["description"],
                category=Category.project,
                source="scaffold",
                ttl_days=None,
            ),
        )

    _write_meta(project_root)
    return True
