from __future__ import annotations

from pathlib import Path


def display_name(file_name: str) -> str:
    return Path(file_name).stem


def display_path(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path.cwd()))
    except ValueError:
        pass

    # Never list path above user: replace C:\Users\<Username> with ~
    p = str(Path(path))
    import re

    # Matches C:\Users\Username\ (case insensitive)
    p = re.sub(r"^[A-Za-z]:\\Users\\[^\\]+\\", r"~\\", p, flags=re.IGNORECASE)
    # Also handle forward slashes just in case
    p = re.sub(r"^[A-Za-z]:/Users/[^/]+/", r"~/", p, flags=re.IGNORECASE)
    return p
