"""Render Markdown to PDF via headless Chromium browser."""

from __future__ import annotations

import re
from pathlib import Path

_MARKDOWN_EXTENSIONS = [
    "tables",
    "fenced_code",
    "sane_lists",
    "attr_list",
    "admonition",
    "pymdownx.details",
    "pymdownx.emoji",
    "pymdownx.superfences",
]

_MARKDOWN_EXTENSION_CONFIGS: dict[str, dict] = {
    "pymdownx.superfences": {
        "custom_fences": [
            {"name": "mermaid", "class": "mermaid"},
        ],
    },
}

_INSTALL_HINT = "Install the 'pdf' extra: uv pip install \"py-teststand-autodoc[pdf]\""


def _load_page_css() -> str:
    """Lazily load the base PDF CSS to avoid module-level side effects."""
    css_path = Path(__file__).parent / "pdf.css"
    if not css_path.exists():
        raise RuntimeError(f"Required CSS file missing: {css_path}")
    return css_path.read_text(encoding="utf-8")


def markdown_to_html(markdown_text: str, custom_css: str | None = None) -> str:
    """Convert Markdown to standalone HTML with print CSS.

    Args:
        custom_css: Optional CSS string to inject (can override accent color).

    """

    try:
        import markdown as markdown_lib
    except ImportError as error:
        raise RuntimeError("markdown is not installed. " + _INSTALL_HINT) from error

    # We no longer import mermaid-py. Mermaid is rendered client-side by Playwright.

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
            escaped_ml = ml.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_line = _meta_re.sub(r"<strong>\1</strong>: ", escaped_ml)
            items.append(f"<div class='meta-item'>{html_line}</div>")
    if items:
        header_html = "<div class='doc-header'>" + "\n".join(items) + "</div>"

    # Mermaid rendered client-side via pymdownx.superfences custom fence

    css = _load_page_css()
    font_path = Path(__file__).parent.parent / "assets" / "UbuntuNerdFont-Regular.ttf"
    if font_path.exists():
        import base64

        font_data = base64.b64encode(font_path.read_bytes()).decode("utf-8")
        font_url = f"data:font/ttf;base64,{font_data}"
        css = css.replace("@@FONT_PATH@@", font_url)
    else:
        css = css.replace("@@FONT_PATH@@", "")

    if custom_css:
        css += "\n" + custom_css
    # Build Markdown extensions configuration
    extension_configs = dict(_MARKDOWN_EXTENSION_CONFIGS)
    try:
        import pymdownx.emoji

        extension_configs["pymdownx.emoji"] = {
            "emoji_index": pymdownx.emoji.twemoji,
            "emoji_generator": pymdownx.emoji.to_svg,
        }
    except ImportError:
        pass

    body = markdown_lib.markdown(
        markdown_text,
        extensions=_MARKDOWN_EXTENSIONS,
        extension_configs=extension_configs,
    )

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

        def block_external(route):
            url = route.request.url
            if url.startswith("file://") or url.startswith("data:"):
                route.continue_()
            else:
                route.abort()

        page.route("**/*", block_external)

        try:
            page.set_content(html, wait_until="load")

            # Load mermaid from bundled assets
            local_mermaid_path = Path(__file__).parent.parent / "assets" / "mermaid.min.js"
            if local_mermaid_path.exists():
                page.add_script_tag(path=local_mermaid_path)
            else:
                raise RuntimeError("Bundled mermaid.min.js not found in assets.")
            page.wait_for_function("typeof mermaid !== 'undefined'")

            page.evaluate("""
                async () => {
                    try {
                        mermaid.initialize({ startOnLoad: false, theme: 'default' });
                        const diagrams = document.querySelectorAll('pre.mermaid');
                        for (let i = 0; i < diagrams.length; i++) {
                            const el = diagrams[i];
                            const code = el.textContent.trim();
                            const { svg } = await mermaid.render('mermaid_' + i, code);
                            el.innerHTML = svg;
                        }
                        document.querySelectorAll('pre.mermaid svg').forEach(svg => {
                            let width = svg.getAttribute('width');
                            let height = svg.getAttribute('height');
                            if (!svg.hasAttribute('viewBox') && width && height) {
                                let w = width.replace(/[^0-9.]/g, '');
                                let h = height.replace(/[^0-9.]/g, '');
                                if (w && h) {
                                    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
                                }
                            }
                            svg.removeAttribute('style');
                        });
                    } catch(e) {
                        console.error('mermaid error:', e);
                    }
                }
            """)

            # Now wait for any images to load and network to settle
            page.wait_for_load_state("networkidle")

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

        content = markdown_path.read_text(encoding="utf-8-sig")
        if (
            content.lstrip().startswith("<?xml")
            or content.lstrip().startswith("<NAME_IN_ATTRIBUTE")
            or content.lstrip().startswith("<teststandfileheader")
        ):
            raise ValueError(
                f"File '{markdown_path.name}' appears to be raw XML content. "
                "The PDF generator requires a Markdown file as input."
            )

        pdf_path = Path(pdf_path) if pdf_path else markdown_path.with_suffix(".pdf")
        html = markdown_to_html(
            content,
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
