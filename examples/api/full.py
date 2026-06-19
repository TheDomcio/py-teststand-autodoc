"""Full: all generate_documentation parameters demonstrated."""

import sys
from pathlib import Path

from py_teststand_autodoc import VALID_SCOPES, generate_documentation


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python full.py <path_to_sequence.seq>")
        sys.exit(1)

    output_path = Path("tmp/examples/output/api-full.md")

    generate_documentation(
        # --- I/O ---
        source=sys.argv[1],
        output=output_path,
        # --- Profile ---
        profile="engineer",
        # --- Content flags ---
        extended_syntax=True,
        ignore_skipped=False,
        include_models=True,
        include_scopes=list(VALID_SCOPES),
        include_station_options=True,
        include_types=True,
        include_file_custom_data_types=True,
        types_attached_only=False,
        estimate_software_delays=True,
        detailed_popup_messages=True,
        # --- Metadata ---
        author="Jan Kowalski",
        company="Yesterday Future Company",
        email="jan.kowalski@example.com",
        version="1.0.0",
        # --- PDF ---
        pdf=True,
        browser="msedge",
        # custom_css=Path("custom.css"),  # uncomment to inject custom CSS
    )

    print(f"Generated Markdown at: {output_path}")
    print(f"Generated PDF at: {output_path.with_suffix('.pdf')}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
