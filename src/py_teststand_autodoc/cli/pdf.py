"""CLI for rendering Markdown docs to PDF via headless Edge (Playwright)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..rendering.pdf import PlaywrightPdfPrinter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render Markdown documentation to PDF with headless Microsoft Edge.",
    )
    parser.add_argument("input", help="Markdown file, or a directory to search recursively")
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory for the PDFs (default: current directory)",
    )
    parser.add_argument(
        "--custom-css",
        help="Path to a custom CSS file to inject into PDF rendering (can override accent color)",
    )
    parser.add_argument(
        "--browser",
        choices=["msedge", "chrome", "chromium"],
        default="msedge",
        help="Chromium channel to use for PDF rendering (default: msedge)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        markdown_files = sorted(input_path.rglob("*.md"))
    else:
        markdown_files = [input_path]

    if not markdown_files:
        print("No Markdown files found.")
        return

    output_dir = Path(args.output) if args.output else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    custom_css_content = None
    if args.custom_css:
        css_path = Path(args.custom_css)
        if css_path.exists():
            custom_css_content = css_path.read_text(encoding="utf-8")
        else:
            print(f"Warning: Custom CSS file not found at {css_path}")

    failures = 0
    last_pdf = None
    try:
        with PlaywrightPdfPrinter(
            custom_css=custom_css_content,
            browser_channel=args.browser,
        ) as printer:
            for markdown_file in markdown_files:
                target = output_dir / (markdown_file.stem + ".pdf")
                try:
                    pdf_path = printer.print_markdown_file(markdown_file, target)
                    print("PDF: " + str(pdf_path))
                    last_pdf = pdf_path
                except RuntimeError as error:
                    failures += 1
                    print("FAILED: " + str(markdown_file) + " - " + str(error), file=sys.stderr)
    except RuntimeError as error:
        print("FAILED: " + str(error), file=sys.stderr)
        sys.exit(1)

    if not failures and len(markdown_files) == 1 and last_pdf:
        import os

        if os.name == "nt":
            os.startfile(last_pdf)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
