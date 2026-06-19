"""04: PDF rendering.

Generate Markdown and render PDF in one call.
"""

import sys
from pathlib import Path

from py_teststand_autodoc import generate_documentation


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python 04_pdf_rendering.py <path_to_sequence.seq>")
        sys.exit(1)

    output_path = Path("tmp/examples/output/api-report.md")

    generate_documentation(
        source=sys.argv[1],
        output=output_path,
        profile="engineer",
        extended_syntax=True,
        pdf=True,
    )

    print(f"Generated PDF at: {output_path.with_suffix('.pdf')}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
