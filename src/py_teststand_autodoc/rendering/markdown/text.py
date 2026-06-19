from __future__ import annotations

import re


def slug(text: str) -> str:
    slug_text = re.sub(r"[^\w]+", "-", text.strip().lower())
    return re.sub(r"-+", "-", slug_text).strip("-")


def sanitize(text: str | None) -> str:
    if text is None:
        return ""
    text = text.replace("\n", " ").strip().replace("|", "\\|")
    text = text.replace("[", "\\[").replace("]", "\\]")
    if "<" in text or ">" in text:
        text = "`" + text.replace("`", "'") + "`"
    return text


def code_span(text: str | None) -> str:
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return ""
    return "`" + text.replace("`", "'").replace("|", "\\|") + "`"
