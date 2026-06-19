"""05: Batch conversion.

Convert all .seq files in a directory to Markdown with one call.
"""

import sys

from py_teststand_autodoc import generate_documentation


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: uv run python 05_batch_workspace_conversion.py <seq_dir> <output_dir>")
        sys.exit(1)

    results = generate_documentation(
        source=sys.argv[1],
        output=sys.argv[2],
        profile="engineer",
        extended_syntax=True,
        batch=True,
    )

    assert isinstance(results, list)
    print(f"Generated {len(results)} files:")
    for path in results:
        print(f"  {path}")
    import os

    os._exit(0)


if __name__ == "__main__":
    main()
