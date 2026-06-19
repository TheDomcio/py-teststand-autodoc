"""CLI for sequencer extraction module."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from py_teststand import Engine

from py_teststand_autodoc.api import Extractor, generate_station_options_report
from py_teststand_autodoc.cli.helpers import render_pdf_cli, shutdown_with_watchdog


def main():
    """Entry point: parse args, init Engine, generate docs."""
    parser = argparse.ArgumentParser(description="Generate Markdown documentation for sequences.")
    parser.add_argument("input", help="Root sequence file (or directory if --batch) to analyze")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Treat input as a directory and recursively convert all .seq files inside it",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output Markdown file (default: current directory with same name as sequence)",
    )
    parser.add_argument(
        "--profile",
        choices=["engineer", "business", "station"],
        default="engineer",
        help="Documentation profile (default: engineer). "
        "'station' generates a standalone station options report.",
    )
    parser.add_argument(
        "--ignore-skipped",
        action="store_true",
        help="Omit skipped steps from documentation",
    )
    parser.add_argument(
        "--models",
        action="store_true",
        help="Include process models in documentation",
    )
    parser.add_argument(
        "--variable-scope",
        nargs="+",
        choices=["Locals", "Parameters", "FileGlobals", "StationGlobals"],
        help="Variable scopes to include in the sequence appendix",
    )
    parser.add_argument("--station", action="store_true", help="Document Station Options")
    parser.add_argument("--types", action="store_true", help="List custom types (TypeUsageList)")
    parser.add_argument(
        "--types-all",
        action="store_true",
        help="Include all custom types, not just those attached to the file",
    )
    parser.add_argument(
        "--file-custom-data-types",
        action="store_true",
        help="List custom data types defined in the file",
    )
    parser.add_argument(
        "--estimate-software-delays",
        action="store_true",
        help="Sum Wait expressions to estimate minimum software delays",
    )
    parser.add_argument(
        "--detailed-popup-messages",
        action="store_true",
        help="Include MessagePopup step details in Mermaid diagrams",
    )
    parser.add_argument("--author", default="Jan Kowalski", help="Author name for the header")
    parser.add_argument(
        "--company",
        default="Yesterday Future Company",
        help="Company name for the header",
    )
    parser.add_argument(
        "--email",
        default="jan.kowalski@example.com",
        help="Author email for the header",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Document version for the header (default: use sequence file version)",
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
    parser.add_argument(
        "--no-path",
        action="store_true",
        help="Hide the source file path subtitle in the header",
    )
    parser.add_argument(
        "--company-logo",
        type=str,
        help="Path to a company logo PNG image file to display in the header",
    )

    args = parser.parse_args()
    if args.pdf and not args.output and not args.batch:
        parser.error("--pdf requires --output or --batch")

    if args.profile == "station":
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
        return

    if args.batch:
        if args.output == "-":
            parser.error("--batch cannot write to stdout (-).")
        input_dir = Path(args.input)
        if not input_dir.is_dir():
            parser.error("--batch requires the input to be a directory.")
        out_dir = Path(args.output) if args.output else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = list(input_dir.rglob("*.seq"))
        if not targets:
            print(f"No .seq files found in {input_dir}")
            sys.exit(0)
    else:
        out_dir = None
        targets = [Path(args.input)]
        if not args.output:
            args.output = str(Path.cwd() / f"{targets[0].stem}.md")

    if args.profile == "engineer":
        include_models = True
        include_scopes = args.variable_scope or ["Locals", "FileGlobals", "Parameters"]
        include_station = args.station
        include_types = args.types
        detailed_popup_messages = True
        file_custom_data_types = True
        types_attached_only = not args.types_all
    else:
        include_models = args.models
        include_scopes = args.variable_scope
        include_station = args.station
        include_types = args.types
        detailed_popup_messages = args.detailed_popup_messages
        file_custom_data_types = args.file_custom_data_types
        types_attached_only = not args.types_all

    engine = Engine()
    try:
        for target in targets:
            print(f"\nProcessing: {target.name}")
            try:
                ext = Extractor(
                    engine,
                    include_process_models=include_models,
                    include_scopes=include_scopes,  # type: ignore[arg-type]
                    include_station_options=include_station,
                    include_types=include_types,
                    include_file_custom_data_types=file_custom_data_types,
                    types_attached_only=types_attached_only,
                    profile=args.profile,
                    ignore_skipped=args.ignore_skipped,
                    extended_syntax=True,
                    estimate_software_delays=args.estimate_software_delays,
                    detailed_popup_messages=detailed_popup_messages,
                    author=args.author,
                    company=args.company,
                    email=args.email,
                    version=args.version,
                    include_path=not args.no_path,
                    company_logo=args.company_logo,
                )
                ext.analyze_hierarchy(str(target))
                md_content = ext.to_markdown()

                if args.batch:
                    if out_dir is None:
                        raise ValueError("out_dir must be set for batch mode")
                    out_path = out_dir / f"{target.stem}.md"
                else:
                    out_path = Path(args.output) if args.output != "-" else "-"

                if out_path == "-":
                    sys.stdout.write(md_content)
                else:
                    if not isinstance(out_path, Path):
                        raise TypeError(f"Expected Path, got {type(out_path)}")
                    with out_path.open("w", encoding="utf-8") as f:
                        f.write(md_content)
                    print(f"Documentation saved to: {out_path}")
                    if args.pdf:
                        render_pdf_cli(out_path, custom_css=args.custom_css, browser=args.browser)
                        if os.name == "nt" and not args.batch:
                            os.startfile(out_path.with_suffix(".pdf"))
            except Exception as e:
                import traceback

                traceback.print_exc()
                print(f"Error processing {target.name}: {e}")
                if not args.batch:
                    sys.stdout.flush()
                    sys.stderr.flush()
                    shutdown_with_watchdog(engine, exit_code=1)
                    os._exit(1)
            finally:
                sys.stdout.flush()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        shutdown_with_watchdog(engine, exit_code=1)
        os._exit(1)

    sys.stdout.flush()
    shutdown_with_watchdog(engine)
    os._exit(0)


if __name__ == "__main__":
    main()
