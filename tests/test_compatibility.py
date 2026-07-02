import shutil
import subprocess
from pathlib import Path

import pytest

from py_teststand_autodoc import Extractor


@pytest.mark.timeout(120)
def test_static_site_generators_compatibility(engine, seq_file):
    """Ensure the generated markdown from REAL sequences is compatible with MkDocs and Zensical.
    Uses the static mkdocs.yml in the project root.
    """
    root_dir = Path(__file__).parent.parent
    docs_dir = root_dir / "tmp" / "output_markdowns"

    valid_examples = [Path(seq_file)]

    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(parents=True)

    index_content = "# Validation Site Index\n\n"

    for seq in valid_examples:
        ext = Extractor(
            engine,
            include_flowcharts=True,
            include_process_models=True,
            include_scopes=["Locals", "Parameters"],
            include_station_options=True,
            include_types=True,
            profile="engineer",
        )
        ext.analyze_hierarchy(str(seq))
        md = ext.to_markdown()

        md_name = f"{seq.stem.replace(' ', '_')}.md"
        (docs_dir / md_name).write_text(md, encoding="utf-8")
        index_content += f"- [{seq.stem}]({md_name})\n"

    (docs_dir / "index.md").write_text(index_content, encoding="utf-8")

    # Run MkDocs
    mkdocs_res = subprocess.run(
        ["uv", "run", "--group", "tests", "mkdocs", "build", "--strict"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    assert mkdocs_res.returncode == 0, f"MkDocs failed:\n{mkdocs_res.stderr}\n{mkdocs_res.stdout}"

    # Run Zensical
    zensical_res = subprocess.run(
        ["uv", "run", "--group", "tests", "zensical", "build"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    assert zensical_res.returncode == 0, (
        f"Zensical failed:\n{zensical_res.stderr}\n{zensical_res.stdout}"
    )
