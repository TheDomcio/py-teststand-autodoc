"""Render Markdown to PDF via headless Chromium browser."""

from __future__ import annotations

import re
from pathlib import Path

_MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "attr_list", "admonition"]

_INSTALL_HINT = "Install the 'pdf' extra: uv pip install \"py-teststand-autodoc[pdf]\""


def _load_page_css() -> str:
    """Lazily load the base PDF CSS to avoid module-level side effects."""
    css_path = Path(__file__).parent / "pdf.css"
    if not css_path.exists():
        raise RuntimeError(f"Required CSS file missing: {css_path}")
    return css_path.read_text(encoding="utf-8")


def make_svg_responsive(svg_content: str) -> str:
    """Make raw SVG responsive to scale down to fit container."""
    match = re.search(r"<svg([^>]+)>", svg_content)
    if not match:
        return svg_content

    attrs_str = match.group(1)

    # Remove fixed width, height, and style attributes to prevent overrides
    attrs_str = re.sub(r"\bwidth\s*=\s*\"[^\"]*\"", "", attrs_str)
    attrs_str = re.sub(r"\bheight\s*=\s*\"[^\"]*\"", "", attrs_str)
    attrs_str = re.sub(r"\bstyle\s*=\s*\"[^\"]*\"", "", attrs_str)

    new_attrs = attrs_str.strip()

    return svg_content[: match.start()] + f"<svg {new_attrs}>" + svg_content[match.end() :]


def markdown_to_html(markdown_text: str, custom_css: str | None = None) -> str:
    """Convert Markdown to standalone HTML with print CSS.

    Args:
        custom_css: Optional CSS string to inject (can override accent color).

    """
    import tempfile

    try:
        import markdown as markdown_lib
    except ImportError as error:
        raise RuntimeError("markdown is not installed. " + _INSTALL_HINT) from error

    try:
        from mermaid import Mermaid
    except ImportError as error:
        raise RuntimeError("mermaid-py is not installed.") from error

    # Extract author/company/version from markdown and build HTML header
    _meta_re = re.compile(r"^\*\*(Author|Company|Email|Version)\*\*:\s*")
    _path_re = re.compile(r"^`([^`]+)`$")
    all_lines = markdown_text.splitlines()

    # Find where metadata starts (first Author/Company/Email/Version line)
    meta_start = -1
    for i, line in enumerate(all_lines):
        if _meta_re.match(line):
            meta_start = i
            break

    # Collect contiguous metadata lines + trailing blank
    meta_lines: list[str] = []
    meta_end = len(all_lines)
    if meta_start >= 0:
        for i in range(meta_start, len(all_lines)):
            if _meta_re.match(all_lines[i]):
                meta_lines.append(all_lines[i])
            elif all_lines[i].strip() == "":
                meta_end = i + 1
                break
            else:
                meta_end = i
                break

    # Also extract the path line (backtick-wrapped) right before metadata
    path_line = ""
    path_idx = -1
    if meta_start >= 0:
        for i in range(meta_start - 1, -1, -1):
            stripped = all_lines[i].strip()
            if stripped == "":
                continue  # skip blank lines between path and metadata
            m = _path_re.match(stripped)
            if m:
                path_line = m.group(1)
                path_idx = i
                break
            break  # non-blank non-path line: stop

    # Build removal range: from path_line (if found) through metadata end
    remove_start = path_idx if path_idx >= 0 else meta_start
    if remove_start >= 0:
        remaining_lines = all_lines[:remove_start] + all_lines[meta_end:]
    else:
        remaining_lines = all_lines
    markdown_text = "\n".join(remaining_lines)

    header_html = ""
    items = []
    if path_line:
        path_style = "font-size:8pt;color:var(--color-muted);"
        items.append(f"<div class='meta-item' style='{path_style}'>{path_line}</div>")
    for ml in meta_lines:
        ml = ml.strip()
        if ml:
            html_line = _meta_re.sub(r"<strong>\1</strong>: ", ml)
            items.append(f"<div class='meta-item'>{html_line}</div>")
    if items:
        header_html = "<div class='doc-header'>" + "\n".join(items) + "</div>"

    # Replace mermaid blocks with SVG rendered via mermaid-py
    def replace_mermaid(match: re.Match) -> str:
        code = match.group(1).strip()
        try:
            m = Mermaid(code)
            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
                temp_path = Path(f.name)
            try:
                m.to_svg(str(temp_path))
                with temp_path.open(encoding="utf-8") as svg_file:
                    svg_content = svg_file.read()
                svg_content = make_svg_responsive(svg_content)
                return (
                    f'<div class="mermaid-diagram" style="text-align: center;">\n'
                    f"{svg_content}\n</div>"
                )
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        except Exception as e:
            return f"<pre>Failed to render diagram: {e}</pre>"

    processed_text = re.sub(
        r"```mermaid\s+(.*?)```",
        replace_mermaid,
        markdown_text,
        flags=re.DOTALL,
    )

    css = _load_page_css()
    if custom_css:
        css += "\n" + custom_css
    body = markdown_lib.markdown(processed_text, extensions=_MARKDOWN_EXTENSIONS)

    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        + css
        + "</style></head><body>"
        + header_html
        + body
        + "</body></html>"
    )


class PlaywrightPdfPrinter:
    """Prints Markdown/HTML to PDF via headless Playwright Chromium session.

    Use as context manager; browser runs via Playwright.
    """

    def __init__(
        self,
        custom_css: str | None = None,
        browser_channel: str = "msedge",
    ) -> None:
        self._custom_css = custom_css
        self._browser_channel = browser_channel
        self._playwright_ctx = None
        self._playwright = None
        self._browser = None

    def __enter__(self) -> PlaywrightPdfPrinter:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("playwright is not installed. " + _INSTALL_HINT) from error

        self._playwright_ctx = sync_playwright()
        self._playwright = self._playwright_ctx.__enter__()
        try:
            self._browser = self._playwright.chromium.launch(
                channel=self._browser_channel,
                headless=True,
            )
        except Exception as error:
            raise RuntimeError(
                f"Failed to launch Chromium channel '{self._browser_channel}': {error}\n"
                "Please ensure the browser is installed on this system.",
            ) from error
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright_ctx:
            self._playwright_ctx.__exit__(exc_type, exc_val, exc_tb)

    def print_html(self, html: str, pdf_path: Path) -> None:
        """Print standalone HTML document to pdf_path."""
        if not self._browser:
            raise RuntimeError("PlaywrightPdfPrinter must be entered as a context manager first")

        page = self._browser.new_page()
        try:
            page.set_content(html, wait_until="networkidle")
            page.pdf(
                path=str(pdf_path.resolve()),
                display_header_footer=False,
                print_background=True,
            )
        except Exception as error:
            raise RuntimeError(f"Playwright PDF print failed: {error}") from error
        finally:
            page.close()

    def print_markdown_file(
        self,
        markdown_path: str | Path,
        pdf_path: str | Path | None = None,
    ) -> Path:
        """Render Markdown file to PDF next to it or at pdf_path."""
        markdown_path = Path(markdown_path)
        pdf_path = Path(pdf_path) if pdf_path else markdown_path.with_suffix(".pdf")
        html = markdown_to_html(
            markdown_path.read_text(encoding="utf-8"),
            custom_css=self._custom_css,
        )
        self.print_html(html, pdf_path)
        return pdf_path


def markdown_file_to_pdf(
    markdown_path: str | Path,
    pdf_path: str | Path | None = None,
    custom_css: str | None = None,
    browser_channel: str = "msedge",
) -> Path:
    """One-shot wrapper around PlaywrightPdfPrinter."""
    with PlaywrightPdfPrinter(custom_css=custom_css, browser_channel=browser_channel) as printer:
        return printer.print_markdown_file(markdown_path, pdf_path)
