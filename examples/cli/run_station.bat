@echo off
set "OUT=examples\output"

if not exist "%OUT%" mkdir "%OUT%"

REM --- Station options report via CLI ---
uv run py-teststand-autodoc-station -o "%OUT%\station_options.md"

REM --- Station profile via main CLI (same result) ---
uv run py-teststand-autodoc "%OUT%\station_options.md" -o "%OUT%\station_from_profile.md" --profile station

REM --- API example ---
uv run python examples\api\station.py
