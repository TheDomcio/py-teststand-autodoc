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
from .markdown.text import code_block, sanitize, slug
from .paths import display_name, display_path
from .step_extras import append_step_extras

_GROUP_ORDER = ("Setup", "Main", "Cleanup")


class Formatter:
    """Converts extracted sequence data into Markdown reports."""

    def __init__(
        self,
        profile: str = "engineer",
        include_flowcharts: bool = True,
        include_station_options: bool = False,
        include_types: bool = False,
        include_file_custom_data_types: bool = False,
        types_attached_only: bool = True,
        author: str = "Jan Kowalski",
        company: str = "Yesterday Future Company",
        email: str = "jan.kowalski@yesterdayfuturecompany.pl",
        version: str = "1.0.0",
        detailed_popup_messages: bool = True,
        show_paths: bool = False,
        company_logo: str | None = None,
    ):
        self.profile = profile.lower()
        self.include_flowcharts = include_flowcharts
        self.include_station_options = include_station_options
        self.include_types = include_types
        self.include_file_custom_data_types = include_file_custom_data_types
        self.types_attached_only = types_attached_only
        self.author = author
        self.company = company
        self.email = email
        self.version = version
        self.detailed_popup_messages = detailed_popup_messages
        self.show_paths = show_paths
        self.company_logo = company_logo

    # ------------------------------------------------------------------ utils

    def _step_description(self, step: dict[str, Any]) -> str:
        """Step description minus sequencer auto-echo of step type."""
        description = step.get("description", "")
        if not description:
            return ""

        # Sequencer often defaults description to step type
        if description.strip().lower() == (step.get("type") or "").strip().lower():
            return ""

        exprs = step.get("expressions", {})
        post_expr = exprs.get("post_expr", "")
        pre_expr = exprs.get("pre_expr", "")

        # TestStand often auto-echos expressions into the description
        if description and (description == post_expr or description == pre_expr):
            return ""

        if post_expr and description == f"#NoValidation({post_expr})":
            return ""

        if description.startswith("#NoValidation(") and description.endswith(")"):
            inner = description[14:-1]
            if inner == post_expr:
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
        if not getattr(self, "include_flowcharts", False):
            return []
        # A one-node diagram repeats the step list without adding flow
        # information, so groups need at least two steps to earn a chart.
        if len(steps) < 2:
            return []
        chart = build_flowchart(
            steps,
            detailed_popup_messages=getattr(self, "detailed_popup_messages", False),
            include_flowcharts=True,
        )
        if not chart:
            return []
        return ["```mermaid", chart, "```", ""]

    # ------------------------------------------------------------ main render

    def format(
        self,
        hierarchy_data: list[dict[str, Any]],
        modules_used: dict[str, list[dict[str, str | int]]],
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
        if self.show_paths and hierarchy_data:
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
            md.append(f"**Email**: <{self.email}>")
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
        output = re.sub(r"[ \t]+\n", "\n", output)
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
        md.append("## " + name)
        md.append("")
        category = sequence.get("category", "Subsequence")
        md.append("*" + category + "*")
        md.append("")
        if self.profile == "engineer" and sequence.get("comment"):
            comment = sanitize(sequence["comment"])
            md.append("> " + comment)
            md.append("")

        if sequence.get("estimated_software_delay"):
            md.append(f"**Minimum Software Delay:** {sequence['estimated_software_delay']}s")
            md.append("")

        if self.profile == "engineer":
            self._append_sequence_variables_inline(md, sequence.get("variables") or {})

        for group_name, steps in self._ordered_groups(sequence["step_groups"]):
            if self.profile == "engineer":
                md.append("### " + group_name)
                md.append("")
            md.extend(self._diagram_block(steps))
            if self.profile == "business":
                if not self.include_flowcharts:
                    self._append_step_list(md, steps)
            else:
                self._append_step_table(md, steps, sequence)

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
                return f"{low} to < {high}"
            elif comp == ">= x <=":
                return f"{low} to {high}"
            elif comp == "> x <":
                return f"> {low} to < {high}"
            elif comp == "> x <=":
                return f"> {low} to {high}"
            else:
                return comp

        if target:
            if target == "True":
                return "Pass"
            if target.startswith("!= "):
                return target
            return f"== {target}"
        elif low and high:
            return f"{low} to {high}"
        elif low:
            return f">= {low}"
        elif high:
            return f"<= {high}"
        return ""

    def _append_step_list(self, md: list[str], steps: list[dict[str, Any]]) -> None:
        """Nested outline of step flow: name, test criteria, description.

        Indentation follows flow-control nesting for readability without Mermaid.
        """
        icon_map = {
            "SeqAdp": ":material-link:",
            "SequenceCall": ":material-link:",
            "MessagePopup": ":material-message-processing:",
            "PassFail": ":material-check-all:",
            "PassFailTest": ":material-check-all:",
            "NumericLimit": ":material-numeric:",
            "NumericLimitTest": ":material-numeric:",
            "StringValue": ":material-format-text:",
            "StringValueTest": ":material-format-text:",
            "Action": ":material-lightning-bolt:",
            "Label": ":material-label:",
            "Statement": ":material-code-tags:",
            "CallExecutable": ":material-application-cog:",
            "Wait": ":material-timer:",
            "NI_Wait": ":material-timer:",
            "PropertyLoader": ":material-database-import:",
            "NI_PropertyLoader": ":material-database-import:",
            "Database": ":material-database:",
            "NI_Database": ":material-database:",
            "NI_OpenDatabase": ":material-database-plus:",
            "NI_CloseDatabase": ":material-database-minus:",
            "NI_OpenSQLStatement": ":material-database-search:",
            "NI_CloseSQLStatement": ":material-database-remove:",
            "NI_DataOperation": ":material-database-cog:",
            "NI_NewCsvFileOutputRecordStream": ":material-file-delimited:",
            "NI_CreateIOSessionAndApplyIOConfig": ":material-swap-horizontal:",
            "NI_CloseIOSession": ":material-power-plug-off:",
            "NI_Notification": ":material-bell:",
            "NI_Rendezvous": ":material-handshake:",
            "NI_Semaphore": ":material-flag:",
            "NI_Lock": ":material-lock:",
            "NI_Queue": ":material-playlist-play:",
            "NI_AutoSchedule": ":material-calendar-clock:",
            "NI_UseAutoScheduledResource": ":material-calendar-clock:",
            "NI_ThreadPriority": ":material-tune:",
            "NI_BatchSpec": ":material-file-cog:",
            "NI_BatchSpecification": ":material-file-cog:",
            "NI_CpuAffinity": ":material-cpu-32-bit:",
            "DotNet": ":material-microsoft-windows:",
            "MultipleNumericLimit": ":material-numeric-9-plus-box:",
            "NI_MultipleNumericLimitTest": ":material-numeric-9-plus-box:",
            "NI_Flow_If": ":material-call-split:",
            "NI_Flow_ElseIf": ":material-call-split:",
            "NI_Flow_Else": ":material-call-split:",
            "NI_Flow_Select": ":material-format-list-checks:",
            "NI_Flow_Case": ":material-format-list-checks:",
            "NI_Flow_For": ":material-sync:",
            "NI_Flow_ForEach": ":material-sync:",
            "NI_Flow_While": ":material-sync:",
            "NI_Flow_DoWhile": ":material-sync:",
            "NI_Flow_Break": ":material-location-exit:",
            "NI_Flow_Continue": ":material-location-enter:",
            "NI_Flow_End": ":material-stop:",
        }

        depth = 0
        for step in steps:
            kind = step["type"]
            if kind == FLOW_END:
                depth = max(0, depth - 1)
                continue
            indent = "  " * depth
            name = sanitize(step["name"]) or "(unnamed)"

            settings = step.get("step_settings", {})
            icon_file = settings.get("Icon", "")
            icon_name = icon_file.replace(".ico", "").replace(".png", "") if icon_file else ""
            emoji = icon_map.get(icon_name, "") or icon_map.get(kind, "")

            run_mode = settings.get("RunMode")
            if run_mode == "Skip":
                name = f"~~{name}~~ (Skipped)"

            exprs = step.get("expressions", {})
            indicators = ""
            if exprs.get("loop_type"):
                indicators += "\uf01e"
            if exprs.get("record_result", "").lower() == "false":
                indicators += "\uf0a2"

            prefix = ""
            if emoji or indicators:
                prefix = f"{indicators}{emoji} "

            anchor = ""

            if is_flow_control(kind):
                desc = sanitize(step.get("description", "")).strip()
                label = desc if desc else name
                text = anchor + prefix + "*" + kind.replace("NI_Flow_", "") + "*: " + label
            else:
                text = anchor + prefix + "**" + name + "**"
                if kind == "SequenceCall":
                    target = step.get("target_sequence", "")
                    if target:
                        text += f" \uf061 [{target}](#{slug(target)})"
                limits = step.get("limits") or {}
                criteria = self._criteria_text(limits)
                if criteria:
                    unit = sanitize(limits.get("unit", "")).strip()
                    unit_str = f" {unit}" if unit else ""
                    text += " (" + criteria + unit_str + ")"
                description = self._step_description(step)
                if description:
                    text += ": " + sanitize(description)

                # Append requirements if present
                reqs = step.get("requirements")
                if reqs:
                    text += f" | Reqs: {', '.join(sanitize(r) for r in reqs)}"

                # Append report text if present
                exprs = step.get("expressions", {})
                if exprs.get("report_text"):
                    text += f" | Report: {sanitize(exprs['report_text'])}"

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
        return expr

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

    def _append_step_table(
        self, md: list[str], steps: list[dict[str, Any]], sequence: dict[str, Any] | None = None
    ) -> None:
        """Render steps as a rich dynamic list instead of a fixed table."""
        executable = [step for step in steps if not is_flow_control(step["type"])]
        if not executable:
            return

        # Resolve target step names from the entire sequence if available
        all_steps = []
        if sequence and "step_groups" in sequence:
            for g_steps in sequence["step_groups"].values():
                all_steps.extend(g_steps)
        else:
            all_steps = steps

        icon_map = {
            "SeqAdp": ":material-link:",
            "SequenceCall": ":material-link:",
            "MessagePopup": ":material-message-processing:",
            "PassFail": ":material-check-all:",
            "PassFailTest": ":material-check-all:",
            "NumericLimit": ":material-numeric:",
            "NumericLimitTest": ":material-numeric:",
            "StringValue": ":material-format-text:",
            "StringValueTest": ":material-format-text:",
            "Action": ":material-lightning-bolt:",
            "Label": ":material-label:",
            "Statement": ":material-code-tags:",
            "CallExecutable": ":material-application-cog:",
            "Wait": ":material-timer:",
            "NI_Wait": ":material-timer:",
            "PropertyLoader": ":material-database-import:",
            "NI_PropertyLoader": ":material-database-import:",
            "Database": ":material-database:",
            "NI_Database": ":material-database:",
            "NI_OpenDatabase": ":material-database-plus:",
            "NI_CloseDatabase": ":material-database-minus:",
            "NI_OpenSQLStatement": ":material-database-search:",
            "NI_CloseSQLStatement": ":material-database-remove:",
            "NI_DataOperation": ":material-database-cog:",
            "NI_NewCsvFileOutputRecordStream": ":material-file-delimited:",
            "NI_CreateIOSessionAndApplyIOConfig": ":material-swap-horizontal:",
            "NI_CloseIOSession": ":material-power-plug-off:",
            "NI_Notification": ":material-bell:",
            "NI_Rendezvous": ":material-handshake:",
            "NI_Semaphore": ":material-flag:",
            "NI_Lock": ":material-lock:",
            "NI_Queue": ":material-playlist-play:",
            "NI_AutoSchedule": ":material-calendar-clock:",
            "NI_UseAutoScheduledResource": ":material-calendar-clock:",
            "NI_ThreadPriority": ":material-tune:",
            "NI_BatchSpec": ":material-file-cog:",
            "NI_BatchSpecification": ":material-file-cog:",
            "NI_CpuAffinity": ":material-cpu-32-bit:",
            "DotNet": ":material-microsoft-windows:",
            "MultipleNumericLimit": ":material-numeric-9-plus-box:",
            "NI_MultipleNumericLimitTest": ":material-numeric-9-plus-box:",
        }

        for index, step in enumerate(executable):
            name = sanitize(step["name"]) or "(unnamed)"
            step_type = sanitize(step.get("type", ""))

            anchor = ""

            settings = step.get("step_settings", {})
            icon_file = settings.get("Icon", "")
            icon_name = icon_file.replace(".ico", "").replace(".png", "") if icon_file else ""
            emoji = icon_map.get(icon_name, "") or icon_map.get(step_type, "")

            run_mode = settings.get("RunMode")

            exprs = step.get("expressions", {})
            indicators = ""
            if exprs.get("loop_type"):
                indicators += "\uf01e"
            if exprs.get("record_result", "").lower() == "false":
                indicators += "\uf0a2"

            prefix = ""
            if emoji or indicators:
                prefix = f"{indicators}{emoji} "

            adapter = sanitize(step.get("adapter", ""))
            adapter_html = ""
            if step_type == "Label":
                adapter_html = ' <span class="adapter adapter-label">Label</span>'
            elif adapter and adapter.lower() != "built-in":
                adapter_class = self._adapter_css_class(adapter)
                if adapter_class:
                    adapter_html = f' <span class="adapter {adapter_class}">{adapter}</span>'
                else:
                    adapter_html = f" `{adapter}`"

            type_html = f' <span class="step-type">{step_type}</span>' if step_type else ""
            # Step header line (no dash)
            if step.get("skipped") or run_mode == "Skip":
                skip_tag = " *(skipped)*"
                md.append(
                    f"{index + 1}. {anchor}{prefix}**~~{name}~~**"
                    f"{adapter_html}{type_html}{skip_tag}"
                )
            else:
                md.append(f"{index + 1}. {anchor}{prefix}**{name}**{adapter_html}{type_html}")

            # Compute attributes
            expr_cell = self._step_expression_cell(step)
            limits = step.get("limits") or {}
            criteria = self._criteria_text(limits)
            precond = step.get("precondition", "")
            desc = self._step_description(step)
            delay = step.get("estimated_software_delay")
            module_path = step.get("module") or ""
            module_info = step.get("module_info") or {}
            extra = module_info.get("extra") or {}

            # Attributes as indented sub-bullets (4-space indent for nesting)
            if expr_cell and step_type != "MessagePopup":
                md.append("    - **Expression**:")
                md.append("")
                md.append(code_block(expr_cell, indent=6))
                md.append("")

            # Module details depending on adapter type
            adapter_lower = adapter.lower()
            if any(x in adapter_lower for x in ("labview", "lv", "g flexible", "g ")):
                # LabVIEW adapter
                vi_path = extra.get("vi_path") or step.get("vi") or ""
                project_path = extra.get("project_path") or ""
                class_path = extra.get("class_path") or ""
                if class_path:
                    md.append(f"    - **Class**: `{class_path}`")
                if vi_path:
                    md.append(f"    - **VI**: `{display_name(vi_path)}`")
                elif project_path:
                    md.append(f"    - **Project**: `{display_name(project_path)}`")
                elif module_path:
                    md.append(f"    - **Module**: `{display_name(module_path)}`")
            elif any(x in adapter_lower for x in ("dotnet", ".net")):
                # .NET adapter
                assembly_name = extra.get("assembly_name") or module_path or ""
                class_name = extra.get("class_name") or ""
                member_name = extra.get("member_name") or ""

                if class_name and member_name:
                    md.append(f"    - **Call**: `{class_name}.{member_name}(...)`")
                elif member_name:
                    md.append(f"    - **Method**: `{member_name}`")

                if assembly_name and assembly_name != "N/A":
                    md.append(f"    - **Assembly**: `{display_name(assembly_name)}`")
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
                    # If target is dynamic, it won't be a valid anchor, but try our best
                    md.append(f"    - **Calls**: [{target}](#{slug(target)})")

            if step_type == "MessagePopup":

                def _strip_quotes(s: str) -> str:
                    s = s.strip()
                    if (s.startswith('"') and s.endswith('"')) or (
                        s.startswith("'") and s.endswith("'")
                    ):
                        return s[1:-1]
                    return s

                title_expr = exprs.get("title")
                message_expr = exprs.get("message")

                if title_expr:
                    md.append("    - **Title Expression**:")
                    md.append("")
                    md.append(code_block(_strip_quotes(title_expr), indent=6))
                    md.append("")

                if message_expr:
                    md.append("    - **Message Expression**:")
                    md.append("")
                    md.append(code_block(_strip_quotes(message_expr), indent=6))
                    md.append("")

                buttons = []
                for b_idx in range(1, 7):
                    lbl = exprs.get(f"button{b_idx}")
                    if lbl:
                        clean_lbl = _strip_quotes(lbl).strip()
                        if clean_lbl:
                            buttons.append(f"Button {b_idx}: `{clean_lbl}`")
                if buttons:
                    md.append("    - **Buttons**:")
                    for btn in buttons:
                        md.append(f"      - {btn}")

                default_btn = exprs.get("default_button")
                timer_btn = exprs.get("timer_button")
                time_wait = exprs.get("time_to_wait")

                if default_btn and default_btn not in ("0", ""):
                    md.append(f"    - **Default Button**: Button {default_btn}")
                if timer_btn and timer_btn not in ("0", ""):
                    md.append(f"    - **Timer Button**: Button {timer_btn}")
                if time_wait and time_wait not in ("0", "0.0", ""):
                    md.append(f"    - **Time to Wait**: {time_wait}s")

            # Branching Navigation
            for _act_key, tgt_key, lbl in [
                ("pass_action", "pass_action_target_id", "Branch (Pass)"),
                ("fail_action", "fail_action_target_id", "Branch (Fail)"),
                ("custom_true_action", "custom_true_target_id", "Branch (Custom True)"),
                ("custom_false_action", "custom_false_target_id", "Branch (Custom False)"),
            ]:
                tgt_id = exprs.get(tgt_key, "").strip().strip('"')
                if tgt_id:
                    tgt_step = next((s for s in all_steps if s.get("id") == tgt_id), None)
                    if tgt_step:
                        tgt_name = tgt_step.get("name") or "Step"
                    else:
                        tgt_name = tgt_id

                    if tgt_name.startswith("ID#:") or "ID#:" in tgt_name:
                        tgt_name = "Target Step"
                    elif tgt_name == "<End>" or tgt_name == "_End_":
                        tgt_name = "End"
                    md.append(f"    - **{lbl}**: `{tgt_name}`")

            if precond:
                md.append("")
                md.append("    - **Precondition**:")
                md.append("")
                md.append(code_block(precond, indent=6))
                md.append("")
            comment = step.get("comment")
            if comment:
                if step_type == "Label":
                    md.append(f'    - **Comment**: <span class="label-comment">{comment}</span>')
                else:
                    md.append(f"    - **Comment**: {comment}")
            if desc:
                if "\n" in desc:
                    md.append("    - **Description**:")
                    md.append("")
                    md.append(code_block(desc, indent=6))
                    md.append("")
                else:
                    if step_type == "Label":
                        lbl_desc = sanitize(desc)
                        md.append(
                            f'    - **Description**: <span class="label-comment">{lbl_desc}</span>'
                        )
                    else:
                        md.append(f"    - **Description**: {sanitize(desc)}")
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
