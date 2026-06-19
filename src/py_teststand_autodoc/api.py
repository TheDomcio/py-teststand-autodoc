"""Sequencer documentation entry points."""

from __future__ import annotations

import logging
import platform
import re
import socket
from pathlib import Path
from typing import Any

from py_teststand import Engine

from .extraction.extractor import HierarchyExtractor
from .rendering.formatter import Formatter

logger = logging.getLogger(__name__)

VALID_SCOPES: tuple[str, ...] = ("Locals", "Parameters", "FileGlobals", "StationGlobals")
"""Valid values for the ``include_scopes`` parameter of :func:`generate_documentation`."""

VALID_PROFILES: tuple[str, ...] = ("engineer", "business", "station")
"""Valid values for the ``profile`` parameter of :func:`generate_documentation`."""

VALID_BROWSERS: tuple[str, ...] = ("msedge", "chrome", "chromium")
"""Valid Chromium channel names for the ``browser`` parameter of :func:`generate_documentation`."""


class Extractor:
    """Main API for generating sequencer documentation."""

    def __init__(
        self,
        engine: Any,
        include_process_models: bool = False,
        include_scopes: list[str] | None = None,
        include_station_options: bool = False,
        include_types: bool = False,
        include_file_custom_data_types: bool = False,
        types_attached_only: bool = True,
        profile: str = "engineer",
        ignore_skipped: bool = False,
        extended_syntax: bool = True,
        estimate_software_delays: bool = False,
        detailed_popup_messages: bool = False,
        author: str = "Jan Kowalski",
        company: str = "Yesterday Future Company",
        email: str = "jan.kowalski@example.com",
        version: str = "1.0.0",
        include_path: bool = False,
        company_logo: str | None = None,
    ):
        """Set up documentation generator.

        Args:
            engine: Sequencer Engine COM object from py_teststand.Engine().
            include_process_models: Include process model sequences in output.
            include_scopes: Variable scopes to include in the Variables appendix.
                Valid values: 'Locals', 'Parameters', 'FileGlobals', 'StationGlobals'
                (see VALID_SCOPES). None skips the appendix entirely.
            include_station_options: Include station configuration table.
            include_types: Include custom type definitions from the file.
            include_file_custom_data_types: Include all data types defined in file.
            types_attached_only: When True, only types referenced by the file are
                listed. When False, all types from the types window are shown.
            profile: Report layout. 'engineer' gives step tables and variables.
                'business' gives a Mermaid flowchart and outline.
            ignore_skipped: Exclude steps in Skip run mode from documentation.
            extended_syntax: Enable rich MkDocs Material syntax (admonitions).
            estimate_software_delays: Sum Wait step expressions to estimate
                minimum software delays per sequence.
            detailed_popup_messages: Show MessagePopup button and timeout details
                in Mermaid flowchart nodes.
            author: Author name printed in the document header.
            company: Company name printed in the document header.
            email: Author email printed in the document header.
            version: Document version string printed in the header.
            include_path: Include source file path subtitle in the header.
            company_logo: Optional path to a PNG logo to display above the author.

        """
        self.engine = engine
        self.extractor = HierarchyExtractor(
            engine,
            include_process_models,
            include_scopes,
            ignore_skipped,
            estimate_software_delays,
            include_file_custom_data_types,
        )
        self.formatter = Formatter(
            profile=profile,
            extended_syntax=extended_syntax,
            include_station_options=include_station_options,
            include_types=include_types,
            include_file_custom_data_types=include_file_custom_data_types,
            types_attached_only=types_attached_only,
            author=author,
            company=company,
            email=email,
            version=version,
            detailed_popup_messages=detailed_popup_messages,
            include_path=include_path,
            company_logo=company_logo,
        )

    def analyze_hierarchy(self, file_path: str, depth: int = 0) -> None:
        """Walk the sequence file and all called subsequences.

        Args:
            file_path: Absolute path to a .seq file.
            depth: Recursion depth for called sequences (0 = top level).

        """
        self.extractor.extract(file_path, depth)

    def to_markdown(self) -> str:
        """Render collected hierarchy data to Markdown."""
        return self.formatter.format(
            self.extractor.hierarchy_data,
            self.extractor.modules_used,
            self.engine,
        )


def generate_station_options_report(engine: Any) -> str:
    """Generate a standalone station options report without sequence input.

    Args:
        engine: Sequencer Engine COM object from py_teststand.Engine().

    Returns:
        Markdown string containing station configuration tables.

    """
    from .rendering.station_options import append_station_options

    md: list[str] = []
    md.append("<!-- markdownlint-disable MD013 MD024 MD036 MD046 MD051 -->")
    md.append("")
    md.append("# Test Station Report")
    md.append("")

    computer_name = socket.gethostname()
    md.append(f"**Computer**: {computer_name}")
    try:
        if engine.current_user:
            user = engine.current_user.login_name.strip()
            if user:
                md.append(f"**User**: {user}")
    except Exception as e:
        logger.debug(f"Could not read current user: {e}")
    try:
        md.append(f"**Engine Version**: {engine.version_string}")
    except Exception as e:
        logger.debug(f"Could not read engine version: {e}")
    md.append(f"**Operating System**: {platform.platform()}")
    md.append("")

    append_station_options(md, engine)
    output = "\n".join(md).strip() + "\n"

    return re.sub(r"\n{3,}", "\n\n", output)


def generate_documentation(
    *,
    source: str | Path = "",
    output: str | Path | None = None,
    profile: str = "engineer",
    extended_syntax: bool = True,
    ignore_skipped: bool = False,
    include_models: bool = False,
    include_scopes: list[str] | None = None,
    include_station_options: bool = False,
    include_types: bool = False,
    include_file_custom_data_types: bool = False,
    types_attached_only: bool = True,
    estimate_software_delays: bool = False,
    detailed_popup_messages: bool = False,
    author: str = "Jan Kowalski",
    company: str = "Yesterday Future Company",
    email: str = "jan.kowalski@example.com",
    version: str = "1.0.0",
    pdf: bool = False,
    custom_css: str | Path | None = None,
    browser: str = "msedge",
    batch: bool | None = None,
    station_report: bool = False,
    include_path: bool = False,
    company_logo: str | None = None,
) -> Path | list[Path] | str:
    """Generate documentation from a sequence file or directory.

    High-level entry point that owns the Engine lifecycle internally.
    User never touches py_teststand directly.

    Args:
        source: Sequence file path, directory (with batch=True), or ""
            for station report.
        output: Output path. Directory for batch, file otherwise.
            None writes next to source. "-" writes to stdout.
        profile: Report layout. 'engineer' gives step tables and variables.
            'business' gives a Mermaid flowchart and outline.
            'station' generates a station options report (ignores source).
        extended_syntax: Enable rich MkDocs Material syntax (admonitions).
        ignore_skipped: Exclude steps in Skip run mode from documentation.
        include_models: Include process model sequences in output.
        include_scopes: Variable scopes to include in the Variables appendix.
            Valid values: 'Locals', 'Parameters', 'FileGlobals', 'StationGlobals'.
            Pass a list of any combination, or None to omit the appendix entirely.
            Example: include_scopes=['Locals', 'Parameters'].
        include_station_options: Include station configuration table.
        include_types: Include custom type definitions from the file.
        include_file_custom_data_types: Include all data types defined in file.
        types_attached_only: When True, only types referenced by the file are
            listed. When False, all types from the types window are shown.
        estimate_software_delays: Sum Wait step expressions to estimate
            minimum software delays per sequence.
        detailed_popup_messages: Show MessagePopup button and timeout details
            in Mermaid flowchart nodes.
        author: Author name printed in the document header.
        company: Company name printed in the document header.
        email: Author email printed in the document header.
        version: Document version string printed in the header.
        pdf: Also render a PDF next to the output file via headless browser.
            Requires the 'pdf' extra (uv sync --extra pdf).
        custom_css: Path to a custom CSS file to inject into PDF rendering.
        browser: Chromium channel for PDF rendering. One of 'msedge', 'chrome',
            or 'chromium'. Defaults to 'msedge' (system Edge, no download needed).
        batch: True forces batch mode on a directory. False forces single-file
            mode. None auto-detects: directory path → batch, file path → single.
        station_report: Generate a standalone station options report without a
            sequence file. Equivalent to profile='station'.

    Returns:
        Single-file mode: Path to the written .md file.
        Batch mode: list of Paths to written .md files.
        Stdout mode (output="-"): raw Markdown string.

    """
    source_path = Path(source) if source else None

    # Station report mode
    if station_report or profile == "station":
        out = Path(output) if output else Path("station_options.md")
        engine = Engine()
        try:
            report = generate_station_options_report(engine)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report, encoding="utf-8")
            if pdf:
                _render_pdf(out, custom_css, browser)
            return out
        finally:
            _shutdown_engine(engine)

    # Determine batch mode
    if batch is None:
        batch = source_path is not None and source_path.is_dir()

    engine = Engine()
    try:
        if batch:
            return _batch_generate(
                source_path,  # type: ignore[arg-type]
                Path(output) if output else None,
                engine,
                profile=profile,
                extended_syntax=extended_syntax,
                ignore_skipped=ignore_skipped,
                include_models=include_models,
                include_scopes=include_scopes,
                include_station_options=include_station_options,
                include_types=include_types,
                include_file_custom_data_types=include_file_custom_data_types,
                types_attached_only=types_attached_only,
                estimate_software_delays=estimate_software_delays,
                detailed_popup_messages=detailed_popup_messages,
                author=author,
                company=company,
                email=email,
                version=version,
                pdf=pdf,
                custom_css=custom_css,
                browser=browser,
                include_path=include_path,
                company_logo=company_logo,
            )

        # Single file mode
        if source_path is None:
            raise ValueError("source_path is required for single-file mode")
        stdout_mode = output == "-"
        if not stdout_mode:
            out_dir = Path(output).parent if output else Path.cwd()
            out_dir.mkdir(parents=True, exist_ok=True)
        out_path = (
            Path(output) if output and not stdout_mode else Path.cwd() / f"{source_path.stem}.md"
        )

        ext = Extractor(
            engine,
            profile=profile,
            extended_syntax=extended_syntax,
            include_process_models=include_models,
            include_scopes=include_scopes,
            include_station_options=include_station_options,
            include_types=include_types,
            include_file_custom_data_types=include_file_custom_data_types,
            types_attached_only=types_attached_only,
            ignore_skipped=ignore_skipped,
            estimate_software_delays=estimate_software_delays,
            detailed_popup_messages=detailed_popup_messages,
            author=author,
            company=company,
            email=email,
            version=version,
            include_path=include_path,
            company_logo=company_logo,
        )
        ext.analyze_hierarchy(str(source_path))
        md_content = ext.to_markdown()

        if stdout_mode:
            return md_content

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md_content, encoding="utf-8")
        if pdf:
            _render_pdf(out_path, custom_css, browser)
        return out_path
    finally:
        _shutdown_engine(engine)


def _batch_generate(
    source_dir: Path,
    out_dir: Path | None,
    engine: Any,
    *,
    profile: str,
    extended_syntax: bool,
    ignore_skipped: bool,
    include_models: bool,
    include_scopes: list[str] | None,
    include_station_options: bool,
    include_types: bool,
    include_file_custom_data_types: bool,
    types_attached_only: bool,
    estimate_software_delays: bool,
    detailed_popup_messages: bool,
    author: str,
    company: str,
    email: str,
    version: str,
    pdf: bool,
    custom_css: str | Path | None,
    browser: str,
    include_path: bool = False,
    company_logo: str | None = None,
) -> list[Path]:
    """Generate documentation for every .seq file under source_dir."""
    if out_dir is None:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = list(source_dir.rglob("*.seq"))
    if not targets:
        return []

    results: list[Path] = []
    for target in targets:
        out_path = out_dir / f"{target.stem}.md"
        try:
            ext = Extractor(
                engine,
                profile=profile,
                extended_syntax=extended_syntax,
                include_process_models=include_models,
                include_scopes=include_scopes,
                include_station_options=include_station_options,
                include_types=include_types,
                include_file_custom_data_types=include_file_custom_data_types,
                types_attached_only=types_attached_only,
                ignore_skipped=ignore_skipped,
                estimate_software_delays=estimate_software_delays,
                detailed_popup_messages=detailed_popup_messages,
                author=author,
                company=company,
                email=email,
                version=version,
                include_path=include_path,
                company_logo=company_logo,
            )
            ext.analyze_hierarchy(str(target))
            md_content = ext.to_markdown()
            out_path.write_text(md_content, encoding="utf-8")
            results.append(out_path)
            if pdf:
                _render_pdf(out_path, custom_css, browser)
        except Exception as e:
            logger.warning(f"Failed to document {target.name}: {e}")
    return results


def _render_pdf(md_path: Path, custom_css: str | Path | None, browser: str) -> None:
    """Render Markdown to PDF via headless browser."""
    from .cli.helpers import render_pdf_cli

    render_pdf_cli(md_path, custom_css=custom_css, browser=browser)


def _shutdown_engine(engine: Any) -> None:
    """Safely shut down the COM engine."""
    import threading

    def target():
        try:
            import gc

            gc.collect()
            engine.shutdown()
            engine.release()
        except Exception as e:
            logger.warning(f"Engine shutdown error: {e}")

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout=1.0)
