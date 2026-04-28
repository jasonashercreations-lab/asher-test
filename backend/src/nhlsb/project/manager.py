"""Project file (.nhlsb) load and save. Just JSON serialization of Project."""
from __future__ import annotations
import json
from pathlib import Path
from ..core.models import Project


def load_project(path: Path) -> Project:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Project.model_validate(data)


def save_project(project: Project, path: Path) -> None:
    Path(path).write_text(
        project.model_dump_json(indent=2),
        encoding="utf-8",
    )


def default_project() -> Project:
    """The factory-default project: live NHL source, default theme/layout."""
    return Project()
