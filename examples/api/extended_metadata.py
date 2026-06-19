"""03: Extended metadata.

Inject author, company, and version into the Markdown header.
"""

import sys
from pathlib import Path

from py_teststand_autodoc import generate_documentation


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python 03_extended_metadata.py <path_to_sequence.seq>")
        sys.exit(1)

    output_path = Path("tmp/examples/output/api-extended.md")

    generate_documentation(
        source=sys.argv[1],
        output=output_path,
        profile="engineer",
        extended_syntax=True,
        include_scopes=["Locals", "Parameters", "FileGlobals", "StationGlobals"],
        include_station_options=True,
        author="Jan Kowalski",
        company="Yesterday Future Company",
        email="jan.kowalski@example.com",
        version="2.4.1",
    )

    print(f"Generated Markdown at: {output_path}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
