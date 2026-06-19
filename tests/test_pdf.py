import pytest

from py_teststand_autodoc.rendering.pdf import markdown_file_to_pdf


@pytest.mark.unit
def test_markdown_to_pdf_with_mermaid(tmp_path, monkeypatch):
    """Test that markdown_to_pdf successfully renders a Mermaid diagram via mocked mermaid-py."""
    import mermaid

    def mock_to_svg(_self, path):
        from pathlib import Path

        tiny_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="red"/></svg>'
        )
        Path(path).write_text(tiny_svg, encoding="utf-8")

    monkeypatch.setattr(mermaid.Mermaid, "to_svg", mock_to_svg)

    md_content = """
# Test Document

Here is a diagram:

```mermaid
graph TD
    A[Start] --> B[End]
```
"""
    md_path = tmp_path / "doc.md"
    pdf_path = tmp_path / "doc.pdf"
    md_path.write_text(md_content, encoding="utf-8")

    markdown_file_to_pdf(md_path, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


@pytest.mark.unit
def test_pdf_generation_with_mermaid(tmp_path, monkeypatch):
    """Test that PlaywrightPdfPrinter can generate a PDF with a Mermaid diagram."""
    import mermaid

    def mock_to_svg(_self, path):
        from pathlib import Path

        tiny_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="red"/></svg>'
        )
        Path(path).write_text(tiny_svg, encoding="utf-8")

    monkeypatch.setattr(mermaid.Mermaid, "to_svg", mock_to_svg)

    md_path = tmp_path / "document.md"
    pdf_path = tmp_path / "document.pdf"

    md_content = """
# Test Document

```mermaid
graph TD
    A[Start] --> B[End]
```
"""
    md_path.write_text(md_content, encoding="utf-8")

    from py_teststand_autodoc.rendering.pdf import PlaywrightPdfPrinter

    with PlaywrightPdfPrinter() as printer:
        printer.print_markdown_file(md_path, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
