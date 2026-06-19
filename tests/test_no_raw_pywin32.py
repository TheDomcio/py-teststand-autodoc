"""Unit tests enforcing the no-raw-pywin32 rule.

CLAUDE.md mandates using py_teststand wrappers instead of raw COM objects.
These tests scan the source tree and fail on any pywin32 usage.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "py_teststand_autodoc"

# Every pattern that signals raw pywin32 / COM access.
_BANNED: list[tuple[re.Pattern[str], str]] = [
    # --- imports -----------------------------------------------------------
    (re.compile(r"\bimport\s+pythoncom\b"), "import pythoncom"),
    (re.compile(r"\bfrom\s+pythoncom\b"), "from pythoncom import ..."),
    (re.compile(r"\bimport\s+win32com\b"), "import win32com"),
    (re.compile(r"\bfrom\s+win32com\b"), "from win32com import ..."),
    # --- raw COM attribute access ------------------------------------------
    (re.compile(r"\._engine\b"), "raw ._engine attribute access"),
    (re.compile(r"\._dispatch\b"), "raw ._dispatch attribute access"),
    (re.compile(r"\.COMObject\b"), "raw .COMObject access"),
]


def _violations(path: Path) -> list[tuple[int, str, str]]:
    """Return [(line_number, pattern_description, line_text)] for *path*."""
    text = path.read_text(encoding="utf-8")
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("if TYPE_CHECKING"):
            continue
        for pattern, desc in _BANNED:
            if pattern.search(line):
                hits.append((lineno, desc, line.rstrip()))
    return hits


def _collect_violations() -> dict[str, list[tuple[int, str, str]]]:
    result: dict[str, list[tuple[int, str, str]]] = {}
    for path in sorted(_SRC.rglob("*.py")):
        rel = str(path.relative_to(_SRC.parent.parent))
        hits = _violations(path)
        if hits:
            result[rel] = hits
    return result


@pytest.mark.unit
class TestNoRawPywin32:
    """Scan every .py file under src/ for forbidden pywin32 patterns."""

    @pytest.fixture(scope="class")
    def violations(self) -> dict[str, list[tuple[int, str, str]]]:
        return _collect_violations()

    def test_no_pywin32_imports(self, violations: dict[str, list[tuple[int, str, str]]]):
        import_hits = {}
        for f, hits in violations.items():
            filtered = [(ln, d, t) for ln, d, t in hits if "import" in d]
            if filtered:
                import_hits[f] = filtered
        msg_lines = []
        for f, hits in sorted(import_hits.items()):
            for ln, desc, line in hits:
                msg_lines.append(f"  {f}:{ln}: {desc}  —  {line}")
        assert not import_hits, "Raw pywin32 imports found:\n" + "\n".join(msg_lines)

    def test_no_raw_com_attribute_access(self, violations: dict[str, list[tuple[int, str, str]]]):
        access_hits = {}
        for f, hits in violations.items():
            filtered = [(ln, d, t) for ln, d, t in hits if "import" not in d]
            if filtered:
                access_hits[f] = filtered
        msg_lines = []
        for f, hits in sorted(access_hits.items()):
            for ln, desc, line in hits:
                msg_lines.append(f"  {f}:{ln}: {desc}  —  {line}")
        assert not access_hits, "Raw COM attribute access found:\n" + "\n".join(msg_lines)

    def test_summary(self, violations: dict[str, list[tuple[int, str, str]]]):
        total = sum(len(h) for h in violations.values())
        files_with = len(violations)
        assert total == 0, f"{total} raw pywin32 violation(s) in {files_with} file(s)"
