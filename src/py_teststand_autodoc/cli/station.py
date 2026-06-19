"""CLI entry point for generating station options documentation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py_teststand import Engine

from py_teststand_autodoc.api import generate_station_options_report
from py_teststand_autodoc.cli.helpers import render_pdf_cli


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a standalone station options report without sequence input.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output Markdown file (default: station_options.md in current directory)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also render a PDF next to the output file via headless browser",
    )
    parser.add_argument(
        "--custom-css",
        type=str,
        help="Path to a custom CSS file to inject into PDF rendering (can override accent color)",
    )
    parser.add_argument(
        "--browser",
        choices=["msedge", "chrome", "chromium"],
        default="msedge",
        help="Chromium channel for PDF rendering (default: msedge)",
    )
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else Path.cwd() / "station_options.md"

    engine = Engine()
    try:
        report = generate_station_options_report(engine)
        output_path.write_text(report, encoding="utf-8")
        print(f"Station options report saved to: {output_path}")

        if args.pdf:
            render_pdf_cli(output_path, custom_css=args.custom_css, browser=args.browser)
    except Exception as error:
        print(f"Error generating station options report: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        engine.shutdown()
        engine.release()


if __name__ == "__main__":
    main()
