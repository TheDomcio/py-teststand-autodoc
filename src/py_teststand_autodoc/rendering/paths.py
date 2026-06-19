from __future__ import annotations

from pathlib import Path


def display_name(file_name: str) -> str:
    return Path(file_name).stem


def display_path(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path.cwd()))
    except ValueError:
        return path
