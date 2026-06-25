import pytest

from py_teststand_autodoc.rendering.pdf import markdown_file_to_pdf


@pytest.mark.unit
def test_markdown_to_pdf_with_mermaid(tmp_path):
    """Test that markdown_to_pdf successfully renders a Mermaid diagram via Playwright."""
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
def test_pdf_generation_with_mermaid(tmp_path):
    """Test that PlaywrightPdfPrinter can generate a PDF with a Mermaid diagram."""
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
