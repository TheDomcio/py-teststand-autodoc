"""Shared CLI helpers for PDF rendering and engine teardown."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

_SHUTDOWN_BUDGET_SECONDS = 5.0


def render_pdf_cli(
    md_path: Path,
    custom_css: str | Path | None = None,
    browser: str = "msedge",
) -> None:
    """Resolve CSS, call markdown_file_to_pdf, print status."""
    from py_teststand_autodoc.rendering.pdf import markdown_file_to_pdf

    css_content = None
    if custom_css:
        css_path = Path(custom_css)
        if css_path.exists():
            css_content = css_path.read_text(encoding="utf-8")
        else:
            print(f"Warning: Custom CSS file not found at {css_path}")

    print("Starting PDF generation...")
    pdf_path = markdown_file_to_pdf(
        md_path,
        custom_css=css_content,
        browser_channel=browser,
    )
    print(f"PDF saved to: {pdf_path}")


def shutdown_with_watchdog(
    engine: Any,
    exit_code: int = 0,
    timeout_seconds: float = _SHUTDOWN_BUDGET_SECONDS,
) -> None:
    """Tear engine down with watchdog. Output already flushed; process exits if overruns."""
    watchdog = threading.Timer(timeout_seconds, lambda: os._exit(exit_code))
    watchdog.daemon = True
    watchdog.start()
    try:
        import gc

        gc.collect()
        engine.shutdown()
        engine.release()
    except Exception:
        pass
    finally:
        watchdog.cancel()
