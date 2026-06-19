@echo off
set "SEQ=%~1"
set "OUT=tmp\examples-output"

if not exist "%OUT%" mkdir "%OUT%"

REM --- Profiles ---
uv run py-teststand-autodoc "%SEQ%" -o "%OUT%\engineer.md" --profile engineer
uv run py-teststand-autodoc "%SEQ%" -o "%OUT%\business.md" --profile business
uv run py-teststand-autodoc "%SEQ%" -o "%OUT%\station.md" --profile station

REM --- Full engineer report ---
uv run py-teststand-autodoc "%SEQ%" -o "%OUT%\full.md" --models --station --types --variable-scope Locals Parameters --ignore-skipped

REM --- Branded business report with PDF ---
uv run py-teststand-autodoc "%SEQ%" -o "%OUT%\branded.md" --profile business --author "Jan Kowalski" --company "Yesterday Future Company" --version "1.0" --pdf

REM --- Batch mode ---
uv run py-teststand-autodoc "%~dp0..\.." --batch -o "%OUT%\batch"

REM --- API examples ---
uv run python examples\api\basic_generation.py "%SEQ%"
uv run python examples\api\business_profile.py "%SEQ%"
uv run python examples\api\extended_metadata.py "%SEQ%"
uv run python examples\api\pdf_rendering.py "%SEQ%"
uv run python examples\api\full.py "%SEQ%"
uv run python examples\api\batch_workspace_conversion.py "%~dp0..\.." "tmp\examples-output\batch_api"
uv run python examples\api\station.py
