"""Sequencer documentation Extractor facade."""

from __future__ import annotations

import logging
from typing import Any

from ..extraction.extractor import HierarchyExtractor
from ..rendering.formatter import Formatter

logger = logging.getLogger(__name__)


class Extractor:
    """Main API for generating sequencer documentation."""

    def __init__(
        self,
        engine: Any,
        include_process_models: bool = False,
        include_scopes: list[str] | None = None,
        include_station_options: bool | None = None,
        include_types: bool = False,
        include_file_custom_data_types: bool = False,
        types_attached_only: bool = True,
        profile: str = "engineer",
        ignore_skipped: bool = False,
        include_flowcharts: bool = True,
        estimate_software_delays: bool = False,
        detailed_popup_messages: bool = True,
        author: str = "Jan Kowalski",
        company: str = "Yesterday Future Company",
        email: str = "jan.kowalski@yesterdayfuturecompany.pl",
        version: str = "1.0.0",
        show_paths: bool = False,
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
            include_flowcharts: Include all possible logic (Preconditions, Loop
                Settings, etc.) in Mermaid flowcharts.
            estimate_software_delays: Sum Wait step expressions to estimate
                minimum software delays per sequence.
            detailed_popup_messages: Show MessagePopup button and timeout details
                in Mermaid flowchart nodes.
            author: Author name printed in the document header.
            company: Company name printed in the document header.
            email: Author email printed in the document header.
            version: Document version string printed in the header.
            show_paths: Include source file path subtitle in the header.
            company_logo: Optional path to a PNG logo to display above the author.

        """
        if include_station_options is None:
            include_station_options = profile == "engineer"

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
            include_flowcharts=include_flowcharts,
            include_station_options=include_station_options,
            include_types=include_types,
            include_file_custom_data_types=include_file_custom_data_types,
            types_attached_only=types_attached_only,
            author=author,
            company=company,
            email=email,
            version=version,
            detailed_popup_messages=detailed_popup_messages,
            show_paths=show_paths,
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
