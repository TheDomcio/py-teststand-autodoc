"""Appendix generation helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .markdown.tables import format_row, format_sep
from .markdown.text import sanitize


def append_variables(
    md: list[str],
    hierarchy_data: list[dict[str, Any]],
    sorted_sequences_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    sequences_with_vars = [
        sequence
        for file_data in hierarchy_data
        for sequence in sorted_sequences_fn(file_data["sequences"])
        if any(sequence.get("variables", {}).values())
    ]
    if not sequences_with_vars:
        return
    md.append("---")
    md.append("")
    md.append("## Variables")
    md.append("")
    for sequence in sequences_with_vars:
        md.append("### " + sequence["name"].strip() + " variables")
        md.append("")
        for scope, variables in sequence["variables"].items():
            if not variables:
                continue
            md.append("#### " + scope)
            md.append("")
            md.append(format_row(["Name", "Type"]))
            md.append(format_sep(2))
            for variable in variables:
                md.append(format_row([sanitize(variable["name"]), sanitize(variable["type"])]))
            md.append("")


def append_modules(md: list[str], modules_used: dict[str, list[dict[str, str]]]) -> None:
    if not modules_used:
        return
    md.append("---")
    md.append("")
    md.append("## Code Modules")
    md.append("")
    md.append(format_row(["File", "Module", "Adapter"]))
    md.append(format_sep(3))
    for file_path, modules in modules_used.items():
        file_name = Path(file_path).name
        for module in modules:
            md.append(
                format_row(
                    [
                        sanitize(file_name),
                        sanitize(module["path"]),
                        sanitize(module["type"]),
                    ],
                ),
            )
    md.append("")


def append_station_options(md: list[str], engine: Any) -> None:
    from .station_options import append_station_options as _impl

    _impl(md, engine)


def append_types(md: list[str], engine: Any, attached_only: bool = True) -> None:
    md.append("---")
    md.append("")
    md.append("## Custom Types")
    md.append("")
    md.append(format_row(["#", "Type"]))
    md.append(format_sep(2))
    if engine is None:
        md.append(format_row(["*(unavailable — no engine)*", ""]))
        md.append("")
        return
    try:
        type_list = engine.get_types()
        has_types = False
        for index in range(type_list.num_types):
            attached = type_list.get_is_type_attached_to_file(index)
            if attached_only and not attached:
                continue
            type_def = type_list.get_type_definition(index)
            type_name = type_def.name if hasattr(type_def, "name") else "Type " + str(index)
            md.append(format_row([str(index), sanitize(type_name)]))
            has_types = True
        if not has_types:
            md.append(format_row(["(none)", ""]))
    except Exception as error:
        md.append(format_row(["Error: " + sanitize(str(error)), ""]))
    md.append("")


def append_file_custom_data_types(md: list[str], custom_data_types: list[dict[str, Any]]) -> None:
    if not custom_data_types:
        return
    md.append("---")
    md.append("")
    md.append("## File Custom Data Types")
    md.append("")
    for type_data in custom_data_types:
        md.append(f"### {sanitize(type_data['name'])}")
        md.append("")
        md.append(f"**Type**: `{sanitize(type_data['type'])}`")
        md.append("")

        if type_data["fields"]:
            md.append(format_row(["Field", "Type"]))
            md.append(format_sep(2))
            for field in type_data["fields"]:
                md.append(format_row([sanitize(field["name"]), sanitize(field["type"])]))
            md.append("")

        if type_data["enumerators"]:
            md.append(format_row(["Enumerator", "Value"]))
            md.append(format_sep(2))
            for enum in type_data["enumerators"]:
                md.append(format_row([sanitize(enum["name"]), str(enum["value"])]))
            md.append("")
