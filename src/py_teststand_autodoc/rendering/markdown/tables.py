from __future__ import annotations


def format_row(cells: list[str]) -> str:
    return "|" + "|".join(cells) + "|"


def format_sep(count: int) -> str:
    return "|" + "|".join(["---"] * count) + "|"
