"""01: Basic usage.

Generate Markdown documentation from a sequence file in one call.
"""

import sys
from pathlib import Path

from py_teststand_autodoc import generate_documentation


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python 01_basic_generation.py <path_to_sequence.seq>")
        sys.exit(1)

    output_path = Path("tmp/examples/output/api-basic.md")

    generate_documentation(
        source=sys.argv[1],
        output=output_path,
        profile="engineer",
    )

    print(f"Generated Markdown at: {output_path}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
