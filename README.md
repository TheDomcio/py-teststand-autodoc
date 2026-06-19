# py-teststand-autodoc

[![PyPI version](https://img.shields.io/pypi/v/py-teststand-autodoc.svg)](https://pypi.org/project/py-teststand-autodoc/)
[![Python versions](https://img.shields.io/pypi/pyversions/py-teststand-autodoc.svg)](https://pypi.org/project/py-teststand-autodoc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OS](https://img.shields.io/badge/OS-Windows-0078D4.svg?logo=windows)](https://www.microsoft.com/windows)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/badge/uv-managed-black?logo=uv)](https://github.com/astral-sh/uv)
[![ty](https://img.shields.io/badge/ty-checked-blue?logo=python)](https://github.com/astral-sh/ty)
[![pyrefly](https://img.shields.io/badge/pyrefly-checked-blue?logo=python)](https://pyrefly.org)
[![TestStand 2016-2026](https://img.shields.io/badge/TestStand-2016--2026-orange.svg)](https://www.ni.com/docs/en-US/bundle/teststand-api-reference/page/tshelp/teststand-api-reference.html)
[![Downloads](https://static.pepy.tech/badge/py-teststand-autodoc)](https://pepy.tech/projects/py-teststand-autodoc)

`py-teststand-autodoc` is an automated rich documentation generator from National Instruments TestStand™ sequence files.

## Table of contents

- [py-teststand-autodoc](#py-teststand-autodoc)
  - [Table of contents](#table-of-contents)
  - [📖 Overview](#-overview)
  - [⚠️Transparency](#️transparency)
  - [🚧 Project Status](#-project-status)
    - [🤖 AI-Assisted Development](#-ai-assisted-development)
  - [🚀 Installation](#-installation)
    - [⚡ Global installation](#-global-installation)
    - [📦 Direct execution](#-direct-execution)
  - [💻 CLI usage](#-cli-usage)
    - [⚙️ Generate report from sequence](#️-generate-report-from-sequence)
      - [🎨 Custom CSS](#-custom-css)
    - [📂 Examples](#-examples)
  - [🔗 Compatibility](#-compatibility)
    - [🖥️ TestStand™ \& Environment](#️-teststand--environment)
    - [🌐 Static Site Generators](#-static-site-generators)
  - [🧰 Technical stack](#-technical-stack)
  - [⚖️ Legal](#️-legal)

---

## 📖 Overview

This project was inspired by [Wovalab Antidoc Add-on for TestStand](https://www.vipm.io/package/wovalab_lib_antidoc_add_on_teststand/), which is built for the
LabVIEW-TestStand ecosystem, because I missed option to easly integrate with Markdown static site generators like
mentioned in [Static Site Generators](#-static-site-generators) and easier integration with actual Python-based tooling.

It can be used in two ways:

1. As a CLI tool
2. As a Python library (via API - see examples)

---

## ⚠️Transparency

This generator does **not** reverse-engineer or natively parse `.seq` files:
uses my other [py-teststand](https://github.com/TheDomcio/py-teststand) project to interact with TestStand™ COM API.
This means you need a valid TestStand™ installation and a proper [TestStand™ License](https://www.ni.com/docs/en-US/bundle/teststand/page/teststand-licensing-options.html) on the machine running the code.

## 🚧 Project Status

This is a hobby project, maintained on a best-effort basis and **not** yet
under active full-time development ahead of the first release. There is no fixed release
schedule or formal support, but feel free to get in touch.

> [!NOTE]
> **Workspaces not currently supported:** `py-teststand-autodoc` currently processes individual sequence files (`.seq`). Full workspace (`.tsw`) support is not yet implemented.

Treat it as experimental: wrapper behaviour may change between releases without notice
(like error catching or high level imports).

If you hit a bug or unexpected behavior, open an issue with a reproducible case. That is the
best way to get it fixed.

For now i prefer lightweight tags based releases (i protected them in repository settings)
instead of fully described ones until reach 1.0.0 release.

### 🤖 AI-Assisted Development

This project leverages Large Language Models (LLMs) to assist with:

- **Codebase audits** and refactoring.
- **Test coverage analysis** and generation.
- **Documentation drafting**.

This is an independent community project. These AI tools are used to optimize
productivity and are **not** an official component of the project, nor do they integrate
with or replace the official
[NIGEL™ AI Advisor](https://www.ni.com/en/support/software-support/nigel-ai.html)
provided by National Instruments. All generated code is manually reviewed by the
maintainer to ensure it meets the project's quality standards.

---

## 🚀 Installation

Install `py-teststand-autodoc` using `uv`.

### ⚡ Global installation

Install the tool globally to use its CLI commands:

```powershell
uv tool install py-teststand-autodoc
```

For PDF support, include the `pdf` extra:

```powershell
uv tool install py-teststand-autodoc[pdf]
```

> ℹ️ PDF generation uses Playwright to drive a headless Chromium browser (Windows 10+ system Edge by default), therefore no separate browser download is required.

### 📦 Direct execution

Run the tool without installing it globally by using `uvx`:

```powershell
uvx py-teststand-autodoc <input_sequence.seq> -o <output_report.md>
```

To generate a PDF directly, include the `pdf` dependency:

```powershell
uvx --with "py-teststand-autodoc[pdf]" py-teststand-autodoc <input_sequence.seq> -o <output_report.md> --pdf
```

---

## 💻 CLI usage

Generate reports using the `py-teststand-autodoc` and `py-teststand-autodoc-pdf` commands.

### ⚙️ Generate report from sequence

```powershell
py-teststand-autodoc <input_sequence.seq> -o <output_report.md> [options]
```

Options:

- `--profile {engineer,business,station}`: Documentation profile (default: `engineer`). The `station` profile generates a standalone station report with station options, station globals, and search directories.
- `--ignore-skipped`: Omit skipped steps.
- `--models`: Include process models.
- `--batch`: Treat input as a directory and recursively convert all `.seq` files inside it.
- `--variable-scope {Locals,Parameters,FileGlobals,StationGlobals}`: Variable scopes for the appendix.
- `--station`: Include station options.
- `--types`: Include custom types.
- `--types-all`: Include all custom types, not just those attached to the file.
- `--file-custom-data-types`: List custom data types defined in the file.
- `--estimate-software-delays`: Sum Wait expressions to estimate minimum software delays.
- `--detailed-popup-messages`: Include MessagePopup step details in Mermaid diagrams.
- `--author <name>`: Author name for the header (default: `Jan Kowalski`).
- `--company <name>`: Company name for the header (default: `Yesterday Future Company`).
- `--email <email>`: Author email for the header.
- `--version <version>`: Document version for the header.
- `--pdf`: Also render a PDF next to the output file via headless browser.
- `--custom-css <path>`: Path to a custom CSS file to inject into PDF rendering (can override accent color).
- `--browser {msedge,chrome,chromium}`: Chromium channel for PDF rendering (default: `msedge`).

#### 🎨 Custom CSS

The default PDF stylesheet is bundled at `src/py_teststand_autodoc/rendering/pdf.css`.

### 📂 Examples

By default, the `engineer` profile generates all [potentially] useful data (process models, variables by their scope, station options, templates, types) and uses the extended Markdown syntax automatically:

```powershell
# Generates a comprehensive engineering report with all data included
py-teststand-autodoc <input_sequence.seq> -o <output_report.md>
```

The `examples/` directory contains sample scripts for the CLI and API usage. Check them out to learn how to integrate `py-teststand-autodoc` into your own scripts!

```text
examples/
├── cli/
│   ├── run_all.bat
│   └── run_station.bat
└── api/
    ├── basic_generation.py
    ├── business_profile.py
    ├── extended_metadata.py
    ├── pdf_rendering.py
    ├── full.py
    ├── batch_workspace_conversion.py
    └── station.py
```

- [cli/run_all.bat](examples/cli/run_all.bat): Runs the CLI with different option combinations (including `--author` and `--profile business`).
- [cli/run_station.bat](examples/cli/run_station.bat): Generates a standalone station options report.
- [api/basic_generation.py](examples/api/basic_generation.py): Shows how to use the Extractor for default markdown.
- [api/business_profile.py](examples/api/business_profile.py): Shows how to generate business logic reports.
- [api/extended_metadata.py](examples/api/extended_metadata.py): Shows how to programmatically pass author, version, and revision metadata.
- [api/pdf_rendering.py](examples/api/pdf_rendering.py): Shows how to programmatically generate PDFs.
- [api/full.py](examples/api/full.py): Demonstrates all `generate_documentation` parameters in one call.
- [api/batch_workspace_conversion.py](examples/api/batch_workspace_conversion.py): Shows how to batch convert entire directories.
- [api/station.py](examples/api/station.py): Shows how to generate a station options report via API.

---

## 🔗 Compatibility

### 🖥️ TestStand™ & Environment

| Component  | Versions     |
|------------|--------------|
| Windows    | 10+          |
| Python     | 3.11 to 3.14 |
| TestStand™ | 2016 to 2026 |

Older TestStand™ engine versions may also work if the underlying COM interfaces have not changed, but they are not explicitly tested.

### 🌐 Static Site Generators

The generated Markdown output is strictly tested and validated for full compatibility with modern static site generators like:

- **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)**
- **[Zensical](https://zensical.org/)**

> Additional Markdown validation using [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)
---

## 🧰 Technical stack

| Tool                                          | Purpose                                      |
|-----------------------------------------------|----------------------------------------------|
| **[uv](https://github.com/astral-sh/uv)**     | Python package and project manager           |
| **[ty](https://github.com/astral-sh/ty)**     | Static type checker for interface validation |
| **[ruff](https://github.com/astral-sh/ruff)** | Linter and code formatter                    |
| **[pyrefly](https://pyrefly.org)**            | Static type checker                          |
| **[pytest](https://pytest.org/)**             | Unit and integration test runner             |
| **[Playwright](https://playwright.dev/)**     | Headless Chromium browser for PDF rendering  |

---

## ⚖️ Legal

TestStand™ is a registered trademark of
[National Instruments Corporation](https://www.ni.com). Refer to
[NI's TestStand™ licensing options](https://www.ni.com/en/shop/teststand.html) for
information on required licenses to operate the TestStand™ engine.

`py-teststand-autodoc` is an independent community project and is not affiliated with, endorsed
by, or maintained by National Instruments or its parent company
[Emerson](https://www.emerson.com). References to the TestStand™ API are made
solely for interoperability purposes.
