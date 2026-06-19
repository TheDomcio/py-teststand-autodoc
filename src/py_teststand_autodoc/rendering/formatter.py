"""Formatter for sequencer sequence Markdown generation.

Two report styles:
- ``business``: Mermaid diagram + compact step list.
- ``engineer``: full step tables, variables, code-module dependencies.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from .appendices import (
    append_file_custom_data_types,
    append_modules,
    append_station_options,
    append_types,
    append_variables,
)
from .flowchart import FLOW_END, FLOW_OPENERS, build_flowchart, is_flow_control
from .markdown.tables import format_row, format_sep
from .markdown.text import code_span, sanitize, slug
from .paths import display_path
from .step_extras import append_step_extras

_GROUP_ORDER = ("Setup", "Main", "Cleanup")


class Formatter:
    """Converts extracted sequence data into Markdown reports."""

    def __init__(
        self,
        profile: str = "engineer",
        extended_syntax: bool = False,
        include_station_options: bool = False,
        include_types: bool = False,
        include_file_custom_data_types: bool = False,
        types_attached_only: bool = True,
        author: str = "Jan Kowalski",
        company: str = "Yesterday Future Company",
        email: str = "jan.kowalski@example.com",
        version: str = "1.0.0",
        detailed_popup_messages: bool = False,
        include_path: bool = False,
        company_logo: str | None = None,
    ):
        self.profile = profile.lower()
        self.extended_syntax = extended_syntax
        self.include_station_options = include_station_options
        self.include_types = include_types
        self.include_file_custom_data_types = include_file_custom_data_types
        self.types_attached_only = types_attached_only
        self.author = author
        self.company = company
        self.email = email
        self.version = version
        self.detailed_popup_messages = detailed_popup_messages
        self.include_path = include_path
        self.company_logo = company_logo

    # ------------------------------------------------------------------ utils

    def _step_description(self, step: dict[str, Any]) -> str:
        """Step description minus sequencer auto-echo of step type."""
        description = sanitize(step.get("description", ""))
        if description == sanitize(step.get("type", "")):
            return ""
        return description

    @staticmethod
    def _ordered_groups(step_groups: dict[str, list[dict[str, Any]]]) -> list[tuple[str, list]]:
        """Yield (group_name, steps) in Setup/Main/Cleanup order, skip empties."""
        result = []
        for name in _GROUP_ORDER:
            steps = step_groups.get(name) or []
            if steps:
                result.append((name, steps))
        return result

    # --------------------------------------------------------------- diagrams

    def _diagram_block(self, steps: list[dict[str, Any]]) -> list[str]:
        # A one-node diagram repeats the step list without adding flow
        # information, so groups need at least two steps to earn a chart.
        if len(steps) < 2:
            return []
        chart = build_flowchart(steps, getattr(self, "detailed_popup_messages", False))
        if not chart:
            return []
        return ["```mermaid", chart, "```", ""]

    # ------------------------------------------------------------ main render

    def format(
        self,
        hierarchy_data: list[dict[str, Any]],
        modules_used: dict[str, list[dict[str, str]]],
        engine: Any = None,
    ) -> str:
        md: list[str] = []
        md.append("<!-- markdownlint-disable MD013 MD024 MD036 MD046 MD051 -->")
        md.append("")

        # Title: file name (centered via CSS)
        file_name = hierarchy_data[0]["name"].replace(".seq", "") if hierarchy_data else "Sequence"
        title = f"{file_name} Logic Overview" if self.profile == "business" else file_name
        md.append("# " + title)
        md.append("")

        # Path subtitle
        if self.include_path and hierarchy_data:
            md.append("`" + display_path(hierarchy_data[0]["path"]) + "`")
            md.append("")

        # Company Logo
        if self.company_logo:
            logo_path = self.company_logo.replace("\\", "/")
            md.append(f"![Company Logo]({logo_path})")
            md.append("")

        # Metadata (extracted to HTML header by PDF renderer)
        md.append(f"**Author**: {self.author}")
        if self.email:
            md.append(f"**Email**: {self.email}")
        md.append(f"**Company**: {self.company}")

        version = self.version
        if not version and hierarchy_data:
            file_ver = hierarchy_data[0].get("file_version", "")
            if file_ver:
                version = file_ver
        if version:
            md.append(f"**Version**: {version}")
        md.append("")

        for file_data in hierarchy_data:
            self._append_file(md, file_data)

        if self.profile == "engineer":
            if self.include_file_custom_data_types:
                all_custom_types = []
                for file_data in hierarchy_data:
                    all_custom_types.extend(file_data.get("custom_data_types", []))
                append_file_custom_data_types(md, all_custom_types)

            append_variables(md, hierarchy_data, self._sorted_sequences)
            append_modules(md, modules_used)
            if self.include_station_options:
                append_station_options(md, engine)
            if self.include_types:
                append_types(md, engine, self.types_attached_only)

        output = "\n".join(md).strip() + "\n"
        return re.sub(r"\n{3,}", "\n\n", output)

    def _append_file(self, md: list[str], file_data: dict[str, Any]) -> None:
        md.append("---")
        md.append("")
        if self.profile == "engineer":
            categories = {}
            for seq in file_data.get("sequences", []):
                cat = seq.get("category", "Subsequence")
                categories[cat] = categories.get(cat, 0) + 1

            if categories:
                md.append("**Sequences**")
                md.append("")
                for cat in sorted(categories.keys()):
                    md.append(f"- {cat}: {categories[cat]}")
                md.append("")

            if file_data.get("estimated_software_delay"):
                md.append(
                    f"**Total Minimum Software Delay:** {file_data['estimated_software_delay']}s",
                )
                md.append("")

            self._append_file_globals(md, file_data.get("file_globals") or [])

        for sequence in self._sorted_sequences(file_data["sequences"]):
            self._append_sequence(md, sequence)

    @staticmethod
    def _sorted_sequences(sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rank = {
            "Entry Point": 0,
            "Model Callback": 1,
            "Engine Callback": 2,
            "Front-End Callback": 3,
            "Callback": 4,
            "Subsequence": 5,
        }
        return sorted(
            sequences,
            key=lambda s: (rank.get(s.get("category", "Subsequence"), 6), s["name"]),
        )

    def _append_sequence(self, md: list[str], sequence: dict[str, Any]) -> None:
        name = sequence["name"].strip()
        md.append("#### " + name)
        md.append("")
        category = sequence.get("category", "Subsequence")
        md.append("*" + category + "*")
        md.append("")
        if self.profile == "engineer" and sequence.get("comment"):
            comment = sanitize(sequence["comment"])
            if self.extended_syntax:
                md.append('!!! info "Description"')
                md.append("    " + comment.replace("\n", "\n    "))
            else:
                md.append("> " + comment)
            md.append("")

        if sequence.get("estimated_software_delay"):
            md.append(f"**Minimum Software Delay:** {sequence['estimated_software_delay']}s")
            md.append("")

        if self.profile == "engineer":
            self._append_sequence_variables_inline(md, sequence.get("variables") or {})

        for group_name, steps in self._ordered_groups(sequence["step_groups"]):
            if self.profile == "engineer":
                md.append("##### " + group_name)
                md.append("")
            md.extend(self._diagram_block(steps))
            if self.profile == "business":
                self._append_step_list(md, steps)
            else:
                self._append_step_table(md, steps)

    def _criteria_text(self, limits: dict[str, Any]) -> str:
        """Human-readable test criteria, e.g. ``10 to 20`` or ``= PASS``."""
        low = sanitize(limits.get("low", "")).strip()
        high = sanitize(limits.get("high", "")).strip()
        target = sanitize(limits.get("target", "")).strip()
        comp = limits.get("comp", "").strip()

        if comp:
            if comp in ("==", "!=", ">", ">=", "<", "<="):
                val = target or low or high
                return f"{comp} {val}"
            elif comp == ">= x <":
                return f">= {low} and < {high}"
            elif comp == ">= x <=":
                return f">= {low} and <= {high}"
            elif comp == "> x <":
                return f"> {low} and < {high}"
            elif comp == "> x <=":
                return f"> {low} and <= {high}"
            else:
                return comp

        if target:
            if target == "True":
                return "Pass"
            if target.startswith("!= "):
                return target
            return f"== {target}"
        elif low and high:
            return f">= {low} and <= {high}"
        elif low:
            return f">= {low}"
        elif high:
            return f"<= {high}"
        return ""

    def _append_step_list(self, md: list[str], steps: list[dict[str, Any]]) -> None:
        """Nested outline of step flow: name, test criteria, description.

        Indentation follows flow-control nesting for readability without Mermaid.
        """
        depth = 0
        for step in steps:
            kind = step["type"]
            if kind == FLOW_END:
                depth = max(0, depth - 1)
                continue
            indent = "  " * depth
            name = sanitize(step["name"]) or "(unnamed)"

            step_id = step.get("id") or ""
            anchor = ""
            if step_id:
                safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", step_id)
                anchor = f'<a id="{safe_id}"></a>'

            if is_flow_control(kind):
                desc = sanitize(step.get("description", "")).strip()
                label = desc if desc else name
                text = anchor + "*" + kind.replace("NI_Flow_", "") + "*: " + label
            else:
                text = anchor + "**" + name + "**"
                if kind == "SequenceCall":
                    target = step.get("target_sequence", "")
                    if target:
                        text += f" → [{target}](#{slug(target)})"
                limits = step.get("limits") or {}
                criteria = self._criteria_text(limits)
                if criteria:
                    unit = sanitize(limits.get("unit", "")).strip()
                    unit_str = f" {unit}" if unit else ""
                    text += " (" + criteria + unit_str + ")"
                description = self._step_description(step)
                if description:
                    text += ": " + description
            md.append(indent + "- " + text)
            if kind in FLOW_OPENERS:
                depth += 1
        md.append("")

    def _step_expression_cell(self, step: dict[str, Any]) -> str:
        """Compact expression summary for step table."""
        exprs = step.get("expressions") or {}
        expr = exprs.get("expression") or exprs.get("title") or exprs.get("message") or ""
        # Skip expressions that are just NameOf(Step)
        if re.match(r"^NameOf\s*\(", expr, re.IGNORECASE):
            return ""
        return code_span(expr)

    def _step_name_cell(self, step: dict[str, Any]) -> str:
        """Bold step name; strikethrough when skipped."""
        name = sanitize(step["name"])
        if step.get("skipped"):
            return "~~" + name + "~~ *(skipped)*"
        return "**" + name + "**"

    _ADAPTER_CLASSES: ClassVar[dict[str, str]] = {
        "labview": "adapter-labview",
        "lv": "adapter-labview",
        ".net": "adapter-dotnet",
        "dotnet": "adapter-dotnet",
        "c#": "adapter-dotnet",
        "vb.net": "adapter-dotnet",
        "activex": "adapter-activex",
        "python": "adapter-python",
        "c/c++ dll": "adapter-native",
        "c/c++": "adapter-native",
        "built-in": "adapter-standalone",
        "sequence": "adapter-sequence",
    }

    @staticmethod
    def _adapter_css_class(adapter: str) -> str:
        """Return CSS class for known adapter technology, empty if unknown."""
        lower = adapter.lower().strip()
        for key, css_class in Formatter._ADAPTER_CLASSES.items():
            if key in lower:
                return css_class
        return ""

    def _append_step_table(self, md: list[str], steps: list[dict[str, Any]]) -> None:
        """Render steps as a rich dynamic list instead of a fixed table."""
        executable = [step for step in steps if not is_flow_control(step["type"])]
        if not executable:
            return
        for index, step in enumerate(executable):
            name = sanitize(step["name"]) or "(unnamed)"
            step_type = sanitize(step.get("type", ""))

            step_id = step.get("id") or ""
            anchor = ""
            if step_id:
                safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", step_id)
                anchor = f'<a id="{safe_id}"></a>'

            # Step header line (no dash)
            if step.get("skipped"):
                md.append(f"{index}. {anchor}**~~{name}~~** *(skipped)*")
            else:
                md.append(f"{index}. {anchor}**{name}**")

            # Compute attributes
            adapter = sanitize(step.get("adapter", ""))
            expr_cell = self._step_expression_cell(step)
            limits = step.get("limits") or {}
            criteria = self._criteria_text(limits)
            precond = step.get("precondition", "")
            desc = self._step_description(step)
            delay = step.get("estimated_software_delay")
            module_path = step.get("module") or ""
            module_info = step.get("module_info") or {}
            extra = module_info.get("extra") or {}

            # Type under step name
            if step_type:
                md.append(f"    - **Type**: `{step_type}`")

            # Attributes as indented sub-bullets (4-space indent for nesting)
            if adapter:
                adapter_class = self._adapter_css_class(adapter)
                if adapter_class:
                    md.append(
                        f'    - **Adapter**: <span class="adapter {adapter_class}">{adapter}</span>'
                    )
                else:
                    md.append(f"    - **Adapter**: `{adapter}`")
            if expr_cell:
                md.append(f"    - **Expression**: {expr_cell}")

            # Module details depending on adapter type
            adapter_lower = adapter.lower()
            if any(x in adapter_lower for x in ("labview", "lv", "g flexible", "g ")):
                # LabVIEW adapter
                vi_path = extra.get("vi_path") or step.get("vi") or ""
                project_path = extra.get("project_path") or ""
                class_path = extra.get("class_path") or ""
                if class_path:
                    md.append(f"    - **Class**: `{class_path}`")
                if project_path:
                    md.append(f"    - **Project**: `{project_path}`")
                if vi_path:
                    md.append(f"    - **VI**: `{vi_path}`")
                elif module_path and module_path != "N/A":
                    md.append(f"    - **VI**: `{module_path}`")
            elif any(x in adapter_lower for x in ("dotnet", ".net")):
                # .NET adapter
                assembly_name = extra.get("assembly_name") or module_path or ""
                class_name = extra.get("class_name") or ""
                member_name = extra.get("member_name") or ""
                if assembly_name and assembly_name != "N/A":
                    md.append(f"    - **Assembly**: `{assembly_name}`")
                if class_name:
                    md.append(f"    - **Class**: `{class_name}`")
                if member_name:
                    md.append(f"    - **Method**: `{member_name}`")
            elif "python" in adapter_lower:
                # Python adapter
                python_module = extra.get("module_path") or module_path or ""
                class_name = extra.get("class_name") or ""
                function_name = extra.get("function_name") or ""
                if python_module and python_module != "N/A":
                    md.append(f"    - **Module**: `{python_module}`")
                if class_name:
                    md.append(f"    - **Class**: `{class_name}`")
                if function_name:
                    md.append(f"    - **Function**: `{function_name}`")
            else:
                # Other adapter
                if module_path and module_path != "N/A":
                    md.append(f"    - **Module**: `{module_path}`")

            if criteria:
                md.append(f"    - **Limits**: {criteria}")
                unit = sanitize(limits.get("unit", "")).strip()
                if unit and unit not in ("boolean", "Text"):
                    md.append(f"    - **Unit**: {unit}")
            if step_type == "SequenceCall":
                target = step.get("target_sequence", "")
                if target:
                    md.append(f"    - **Calls**: [{target}](#{slug(target)})")
            if precond:
                md.append(f"    - **Precondition**: `{code_span(precond)}`")
            comment = step.get("comment")
            if comment:
                md.append(f"    - **Comment**: {comment}")
            if desc:
                md.append(f"    - **Description**: {desc}")
            if delay:
                md.append(f"    - **Delay**: {delay}s")

            append_step_extras(md, step, indent="    ")

        md.append("")

    # --------------------------------------------------------- engineer extras

    def _append_file_globals(self, md: list[str], globals_list: list[dict[str, Any]]) -> None:
        """Render File Globals table if any exist."""
        if not globals_list:
            return
        md.append("**File Globals**")
        md.append("")
        md.append(format_row(["Name", "Type"]))
        md.append(format_sep(2))
        for var in globals_list:
            name = sanitize(var.get("name", ""))
            type_name = sanitize(var.get("type", ""))
            md.append(format_row([name, type_name]))
        md.append("")

    def _append_sequence_variables_inline(
        self,
        md: list[str],
        variables: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Render Locals/Parameters/FileGlobals tables inline before step groups."""
        for scope in ("Parameters", "Locals", "FileGlobals"):
            var_list = variables.get(scope) or []
            if not var_list:
                continue
            md.append(f"**{scope}**")
            md.append("")
            md.append(format_row(["Name", "Type"]))
            md.append(format_sep(2))
            for var in var_list:
                md.append(
                    format_row([sanitize(var.get("name", "")), sanitize(var.get("type", ""))]),
                )
            md.append("")
