"""06: Station options report.

Generate a standalone station options report without a sequence file.
"""

from pathlib import Path

from py_teststand_autodoc import generate_documentation


def main() -> None:
    output_path = Path("station_options_report.md")

    generate_documentation(
        output=output_path,
        station_report=True,
    )

    print(f"Station options report saved to: {output_path}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
