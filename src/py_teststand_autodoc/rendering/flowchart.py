"""Build styled Mermaid control-flow diagram from sequencer step group.

Reconstructs NI flow-control markers (If/ElseIf/Else, Select/Case, loops,
Break/Continue, End) into Mermaid flowchart. Decisions as diamonds, loops
with back edges, SequenceCall as subroutines, other steps as boxes.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

# NI flow-control step type names (Sequencer built-in step types).
# They map directly to control flow logic in the Mermaid diagram.
FLOW_IF = "NI_Flow_If"
FLOW_ELSEIF = "NI_Flow_ElseIf"
FLOW_ELSE = "NI_Flow_Else"
FLOW_END = "NI_Flow_End"
FLOW_SELECT = "NI_Flow_Select"
FLOW_CASE = "NI_Flow_Case"
FLOW_BREAK = "NI_Flow_Break"
FLOW_CONTINUE = "NI_Flow_Continue"

FLOW_LOOPS = frozenset(
    {
        "NI_Flow_For",
        "NI_Flow_ForEach",
        "NI_Flow_While",
        "NI_Flow_DoWhile",
        "NI_Flow_StreamLoop",
        "NI_Flow_SweepLoop",
    },
)
# Step types that open a nesting block in the textual outline.
FLOW_OPENERS = FLOW_LOOPS | {FLOW_IF, FLOW_SELECT, FLOW_CASE}

_CLASS_DEFS = [
    "    classDef decision fill:#fff3cd,stroke:#e0a800,color:#212529;",
    "    classDef loop fill:#d1ecf1,stroke:#117a8b,color:#212529;",
    "    classDef seqcall fill:#e2e3f5,stroke:#4b4fa6,color:#212529;",
    "    classDef jump fill:#f8d7da,stroke:#c82333,color:#212529;",
    "    classDef action fill:#f3f4f6,stroke:#6c757d,color:#212529;",
    "    classDef popup fill:#fff9c4,stroke:#f9a825,color:#212529;",
    "    classDef timer fill:#e8f5e9,stroke:#388e3c,color:#212529;",
    "    classDef label fill:#fcf8e3,stroke:#faebcc,color:#8a6d3b,stroke-dasharray: 5 5;",
]

_SHAPE_CLASS = {
    "decision": "decision",
    "loop": "loop",
    "call": "seqcall",
    "jump": "jump",
    "box": "action",
    "popup": "popup",
    "timer": "timer",
    "label": "label",
}


def translate_expression(expr: str) -> str:
    """Make TestStand expressions more human-readable for diagrams."""
    if not expr:
        return expr

    # Previous Step Status
    expr = re.sub(
        r'RunState\.PreviousStep\.Result\.Status\s*==\s*["\']Passed["\']',
        "Previous Step Passed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r'RunState\.PreviousStep\.Result\.Status\s*==\s*["\']Failed["\']',
        "Previous Step Failed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r'RunState\.PreviousStep\.Result\.Status\s*!=\s*["\']Passed["\']',
        "Previous Step NOT Passed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r'RunState\.PreviousStep\.Result\.Status\s*!=\s*["\']Failed["\']',
        "Previous Step NOT Failed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r"RunState\.PreviousStep\.Result\.PassFail\s*==\s*True",
        "Previous Step Passed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r"RunState\.PreviousStep\.Result\.PassFail\s*==\s*False",
        "Previous Step Failed",
        expr,
        flags=re.IGNORECASE,
    )

    # Current Step Status
    expr = re.sub(
        r'Step\.Result\.Status\s*==\s*["\']Passed["\']', "Step Passed", expr, flags=re.IGNORECASE
    )
    expr = re.sub(
        r'Step\.Result\.Status\s*==\s*["\']Failed["\']', "Step Failed", expr, flags=re.IGNORECASE
    )
    expr = re.sub(
        r'Step\.Result\.Status\s*!=\s*["\']Passed["\']',
        "Step NOT Passed",
        expr,
        flags=re.IGNORECASE,
    )
    expr = re.sub(
        r'Step\.Result\.Status\s*!=\s*["\']Failed["\']',
        "Step NOT Failed",
        expr,
        flags=re.IGNORECASE,
    )

    # Cleanup prefix boilerplate
    expr = expr.replace("RunState.PreviousStep.", "PreviousStep.")
    expr = expr.replace("Step.Result.", "")
    return expr


def diagram_label(text: str, fallback: str, max_length: int = 80) -> str:
    """Short, quote-safe label for Mermaid node or edge."""
    label = translate_expression(text or "").strip() or fallback
    label = label.replace("\n", " ").replace('"', "'").replace("|", "/")
    if len(label) > max_length:
        label = label[: max_length - 3].rstrip() + "..."
    return label


def _normalize_wait(raw: str) -> str:
    """Normalize wait time: strip quotes, add 's' suffix, clean leading dot."""
    val = raw.strip().strip("\"'")
    try:
        t = float(val)
        if t == int(t):
            return f"{int(t)}s"
        return f"{t}s"
    except ValueError:
        return val if val else "0s"


def is_flow_control(step_type: str) -> bool:
    """True for any NI flow-control step type."""
    return step_type.startswith("NI_Flow_")


def build_flowchart(
    steps: list[dict[str, Any]],
    detailed_popup_messages: bool = True,
    include_flowcharts: bool = True,
) -> str:
    """Return Mermaid source for a step group, or empty string if there is none."""
    if not steps:
        return ""

    node_lines: list[str] = []
    edge_lines: list[str] = []
    click_lines: list[str] = []
    counter = {"n": 0}
    # pending: edges waiting to attach to the next node, as (source_id, label).
    pending: list[tuple[str, str | None]] = []
    stack: list[dict[str, Any]] = []

    # Build per-step indices keyed by original list position so duplicate names
    # each get their own correct index for cross-referencing with the step table.
    exec_idx_by_pos: dict[int, int] = {}
    exec_idx = 0
    for pos, step in enumerate(steps):
        if not is_flow_control(step.get("type", "")):
            exec_idx_by_pos[pos] = exec_idx
            exec_idx += 1

    # Name → list of original positions, consumed front-to-back as nodes are added.
    name_positions: dict[str, deque[int]] = defaultdict(deque)
    for pos, step in enumerate(steps):
        if pos in exec_idx_by_pos:
            name_positions[step.get("name", "")].append(pos)

    nid_by_step_id: dict[str, str] = {}

    def new_id() -> str:
        counter["n"] += 1
        return "n" + str(counter["n"])

    icon_map = {
        "SeqAdp": "\uf0c1",
        "SequenceCall": "\uf0c1",
        "MessagePopup": "\uf075",
        "PassFail": "\uf00c",
        "PassFailTest": "\uf00c",
        "NumericLimit": "\uf292",
        "NumericLimitTest": "\uf292",
        "StringValue": "\uf031",
        "StringValueTest": "\uf031",
        "Action": "\uf0e7",
        "Label": "\uf02b",
        "Statement": "\uf121",
        "CallExecutable": "\uf013",
        "Wait": "\uf017",
        "NI_Wait": "\uf017",
        "PropertyLoader": "\uf1c0",
        "NI_PropertyLoader": "\uf1c0",
        "Database": "\uf1c0",
        "NI_Database": "\uf1c0",
        "NI_OpenDatabase": "\uf1c0",
        "NI_CloseDatabase": "\uf1c0",
        "NI_OpenSQLStatement": "\uf1c0",
        "NI_CloseSQLStatement": "\uf1c0",
        "NI_DataOperation": "\uf0ce",
        "NI_NewCsvFileOutputRecordStream": "\uf15c",
        "NI_CreateIOSessionAndApplyIOConfig": "\uf1e6",
        "NI_CloseIOSession": "\uf1e6",
        "NI_Notification": "\uf0f3",
        "NI_Rendezvous": "\uf0c0",
        "NI_Semaphore": "\uf024",
        "NI_Lock": "\uf023",
        "NI_Queue": "\uf0cb",
        "NI_AutoSchedule": "\uf073",
        "NI_UseAutoScheduledResource": "\uf073",
        "NI_ThreadPriority": "\uf0dc",
        "NI_BatchSpec": "\uf15c",
        "NI_BatchSpecification": "\uf15c",
        "NI_CpuAffinity": "\uf2db",
        "DotNet": "\uf17a",
        "MultipleNumericLimit": "\uf292",
        "NI_MultipleNumericLimitTest": "\uf292",
        "NI_Flow_If": "",
        "NI_Flow_ElseIf": "",
        "NI_Flow_Else": "",
        "NI_Flow_Select": "",
        "NI_Flow_Case": "",
        "NI_Flow_For": "\uf01e",
        "NI_Flow_ForEach": "\uf01e",
        "NI_Flow_While": "\uf01e",
        "NI_Flow_DoWhile": "\uf01e",
        "NI_Flow_Break": "\uf08b",
        "NI_Flow_Continue": "\uf090",
        "NI_Flow_End": "",
    }

    def add_node(shape: str, label: str, step: dict[str, Any] | str = "") -> str:
        nid = new_id()
        step_name = ""
        step_id = ""
        kind = ""
        run_mode: str | None = None
        if isinstance(step, dict):
            step_name = step.get("name", "")
            step_id = step.get("id") or ""
            kind = step.get("type", "")
        else:
            step_name = step

        # Pop the next position for this name and look up its index.
        pos_queue = name_positions.get(step_name)
        if pos_queue:
            pos = pos_queue.popleft()
            idx = exec_idx_by_pos.get(pos)
            if idx is not None:
                label = f"{idx + 1}. {label}"

        if isinstance(step, dict):
            settings = step.get("step_settings", {})
            icon_file = settings.get("Icon", "")
            icon_name = icon_file.replace(".ico", "").replace(".png", "") if icon_file else ""
            emoji = icon_map.get(icon_name, "") or icon_map.get(kind, "")
            if emoji:
                label = f"{emoji} {label}"

            run_mode = settings.get("RunMode")

            exprs = step.get("expressions") or {}
            limits = step.get("limits") or {}
            extras = []

            # Indicator badges
            indicators = ""
            if exprs.get("pre_expr"):
                indicators += "[Pre]"
            if exprs.get("loop_type"):
                indicators += "[Loop]"
            if exprs.get("record_result", "").lower() == "false":
                indicators += "[NoRec]"

            if indicators:
                label = f"{indicators} {label}"

            if limits:

                def _fmt(v: Any) -> str:
                    try:
                        f = float(v)
                        if f.is_integer():
                            return str(int(f))
                        return str(v) if isinstance(v, str) and not v.endswith(".0") else str(f)
                    except (ValueError, TypeError):
                        return str(v)

                units = limits.get("units", "")
                unit_suffix = f" {units}" if units else ""
                limit_str = ""

                if "string" in limits:
                    limit_str = f"== {limits['string']}"
                elif "target" in limits:
                    limit_str = f"== {_fmt(limits['target'])}"
                else:
                    comp = limits.get("comp", "").upper()
                    low = _fmt(limits.get("low", ""))
                    high = _fmt(limits.get("high", ""))

                    if comp in ("LOGAND", "GELE", "GTLT", "GTLE", "GELT") and low and high:
                        limit_str = f"{low} to {high}{unit_suffix}"
                    elif comp in ("EQ", "==") and low == high:
                        limit_str = f"== {low}{unit_suffix}"
                    elif comp in ("GE", ">=") and low:
                        limit_str = f">= {low}{unit_suffix}"
                    elif comp in ("GT", ">") and low:
                        limit_str = f"> {low}{unit_suffix}"
                    elif comp in ("LE", "<=") and high:
                        limit_str = f"<= {high}{unit_suffix}"
                    elif comp in ("LT", "<") and high:
                        limit_str = f"< {high}{unit_suffix}"
                    elif comp in ("NE", "!=") and low:
                        limit_str = f"!= {low}{unit_suffix}"
                    if limit_str:
                        extras.append(f"Limits: {diagram_label(limit_str, '', 80)}")

                if exprs.get("pre_expr"):
                    extras.append(f"Pre: {diagram_label(exprs['pre_expr'], '', 80)}")
                if exprs.get("post_expr"):
                    extras.append(f"Post: {diagram_label(exprs['post_expr'], '', 80)}")
                if exprs.get("status_expr"):
                    extras.append(f"Status: {diagram_label(exprs['status_expr'], '', 80)}")
                if exprs.get("loop_type"):
                    extras.append(f"Loop: {exprs['loop_type']}")
                if exprs.get("report_text"):
                    extras.append(f"Report: {diagram_label(exprs['report_text'], '', 80)}")
                if exprs.get("record_result"):
                    extras.append(f"Record: {exprs['record_result']}")

            if settings:
                if settings.get("Load Opt"):
                    extras.append(f"Load: {settings['Load Opt']}")
                if settings.get("Unload Opt"):
                    extras.append(f"Unload: {settings['Unload Opt']}")

            if extras:
                label += "<br/>" + "<br/>".join(f"<i>{e}</i>" for e in extras)

        quoted = '"' + label + '"'
        if shape == "decision":
            body = nid + "{" + quoted + "}"
        elif shape == "loop":
            body = nid + "([" + quoted + "])"
        elif shape == "call":
            body = nid + "[[" + quoted + "]]"
        elif shape == "timer":
            body = nid + "(" + quoted + ")"
        elif shape == "jump":
            body = nid + ">" + quoted + "]"
        else:
            body = nid + "[" + quoted + "]"
        node_lines.append("    " + body + ":::" + _SHAPE_CLASS.get(shape, "action"))

        # Override node style if step is skipped
        if isinstance(step, dict) and run_mode == "Skip":
            node_lines.append(f"    style {nid} stroke-dasharray: 5 5,color:#a0a0a0,stroke:#a0a0a0")

        # Add link to anchor in Markdown using Step's unique ID
        if step_id:
            nid_by_step_id[step_id] = nid
            import re

            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", step_id)
            click_lines.append(f'    click {nid} href "#{safe_id}"')

        return nid

    def attach(nid: str) -> None:
        for source, label in pending:
            if label:
                edge_lines.append("    " + source + ' -->|"' + label + '"| ' + nid)
            else:
                edge_lines.append("    " + source + " --> " + nid)
        pending.clear()

    def close_dangling_case() -> None:
        # In the sequencer a Select holds Case blocks each closed by their own End;
        # if one is still open when the next Case arrives, finish it first.
        if stack and stack[-1]["kind"] == "case":
            case_frame = stack.pop()
            case_frame["switch"]["case_tails"].extend(pending)
            pending.clear()

    for step in steps:
        step_type = step.get("type", "")
        name = step.get("name", "")
        # Flow-control steps store their condition in expressions; show it in
        # the diagram so a decision node reads as the actual test, not just "If".
        condition = step.get("expressions", {}).get("expression", "") or step.get("description", "")

        if step_type == FLOW_IF:
            nid = add_node("decision", "If: " + diagram_label(condition or name, "If"), step)
            attach(nid)
            stack.append({"kind": "if", "open_no": nid, "tails": []})
            pending[:] = [(nid, "yes")]
            continue

        if step_type == FLOW_SELECT:
            nid = add_node("decision", "Select: " + diagram_label(condition or name, "value"), step)
            attach(nid)
            stack.append({"kind": "switch", "decision": nid, "case_tails": [(nid, "no match")]})
            pending.clear()
            continue

        if step_type == FLOW_ELSEIF and stack and stack[-1]["kind"] == "if":
            frame = stack[-1]
            frame["tails"].extend(pending)
            label = "Else If: " + diagram_label(condition or name, "Else If")
            nid = add_node("decision", label, step)
            edge_lines.append("    " + frame["open_no"] + ' -->|"no"| ' + nid)
            frame["open_no"] = nid
            pending[:] = [(nid, "yes")]
            continue

        if step_type == FLOW_ELSE and stack and stack[-1]["kind"] == "if":
            frame = stack[-1]
            frame["tails"].extend(pending)
            pending[:] = [(frame["open_no"], "no")]
            frame["open_no"] = None
            continue

        if step_type == FLOW_CASE:
            close_dangling_case()
            if stack and stack[-1]["kind"] == "switch":
                switch_frame = stack[-1]
                stack.append({"kind": "case", "switch": switch_frame})
                pending[:] = [(switch_frame["decision"], diagram_label(name, "case"))]
                continue

        if step_type in FLOW_LOOPS:
            nid = add_node("loop", "Loop: " + diagram_label(condition or name, "loop"), step)
            attach(nid)
            stack.append({"kind": "loop", "header": nid, "break_tails": [], "continue_tails": []})
            pending[:] = [(nid, "each")]
            continue

        if step_type == FLOW_END and stack:
            frame = stack.pop()
            if frame["kind"] == "loop":
                header = frame["header"]
                for source, _label in pending:
                    edge_lines.append("    " + source + ' -->|"repeat"| ' + header)
                for source, _label in frame.get("continue_tails", []):
                    edge_lines.append("    " + source + ' -->|"continue"| ' + header)
                pending[:] = [(header, "exit"), *frame.get("break_tails", [])]
            elif frame["kind"] == "case":
                frame["switch"]["case_tails"].extend(pending)
                pending.clear()
            elif frame["kind"] == "switch":
                pending[:] = list(frame["case_tails"]) + list(pending)
            else:  # if
                tails = list(frame["tails"]) + list(pending)
                if frame.get("open_no"):
                    tails.append((frame["open_no"], "no"))
                pending[:] = tails
            continue

        if step_type in (FLOW_BREAK, FLOW_CONTINUE):
            nid = add_node("action", diagram_label(name, "Action"), step)
            # Find the innermost loop frame
            loop_frame = next((f for f in reversed(stack) if f["kind"] == "loop"), None)
            if loop_frame:
                if step_type == FLOW_BREAK:
                    loop_frame["break_tails"].append((nid, "break"))
                else:
                    loop_frame["continue_tails"].append((nid, "continue"))
            pending.clear()
            continue

        if detailed_popup_messages and step_type == "MessagePopup":
            exprs = step.get("expressions", {})
            msg = exprs.get("message", "").replace('"', "'")
            timeout = exprs.get("time_to_wait", "")
            default_btn = exprs.get("default_button", "")
            timer_btn = exprs.get("timer_button", "")

            label = f"<b>{name}</b>"
            if msg:
                label += f"<br/><i>{msg}</i>"

            buttons = []
            for i in range(1, 7):
                btn_label = exprs.get(f"button{i}", "").strip(" \"'")
                if btn_label:
                    buttons.append(f"[{i}: {btn_label}]")

            if buttons:
                label += "<br/>" + " ".join(buttons)

            if default_btn and len(buttons) > 1:
                label += f"<br/><i>(Default: {default_btn})</i>"

            if timeout and timeout not in ("0", "0.0"):
                wait_text = f"Timeout: {timeout}s"
                if timer_btn:
                    wait_text += f" → triggers [{timer_btn}]"
                label += f"<br/><b>{wait_text}</b>"

            nid = add_node("popup", diagram_label(label, "Popup", max_length=256), step)
            attach(nid)
            pending[:] = [(nid, None)]
            continue

        # Wait steps: UML timer symbol with normalized duration
        if step_type in ("NI_Wait", "Wait"):
            exprs = step.get("expressions", {})
            raw_time = exprs.get("time_to_wait") or exprs.get("expression") or ""
            wait_label = _normalize_wait(raw_time) if raw_time else name
            nid = add_node("timer", diagram_label(f"\uf017 {wait_label}", "Wait"), step)
            attach(nid)
            pending[:] = [(nid, None)]
            continue

        # SequenceCall: link to target sequence in same file
        if step_type == "SequenceCall":
            target = step.get("target_sequence", "")
            label_text = name
            if target:
                label_text = f"{name} → {target}"
            nid = add_node("call", diagram_label(label_text, "Call"), step)
            attach(nid)
            pending[:] = [(nid, None)]
            continue

        logic = step.get("logic", {}) if include_flowcharts else {}
        pre_expr = logic.get("pre_expression")
        post_expr = logic.get("post_expression")
        status_expr = logic.get("status_expression")
        loop_type = logic.get("loop_type", 0)

        # 1. Pre-expression / Precondition
        if pre_expr:
            pre_nid = add_node(
                "action", diagram_label(f"Pre: {pre_expr}", "PreExpr", max_length=64)
            )
            attach(pre_nid)
            pending[:] = [(pre_nid, None)]

        # 2. Step-Level Loop Header
        loop_nid = None
        if loop_type and str(loop_type) not in ("0", "NoLooping", "LoopType_NoLoop"):
            loop_nid = add_node("loop", diagram_label(f"Step Loop ({loop_type})", "Loop"))
            attach(loop_nid)
            pending[:] = [(loop_nid, "each")]

        # 3. Main Step Node
        shape = "box"
        if step_type == "Label":
            shape = "label"
        elif step_type == "MessagePopup":
            shape = "popup"

        main_label = diagram_label(name, step_type or "Step")
        if status_expr:
            main_label += f"<br/><i>Status: {diagram_label(status_expr, '', max_length=64)}</i>"

        nid = add_node(shape, main_label, step)
        attach(nid)

        # 4. Step-Level Loop Footer
        if loop_nid:
            edge_lines.append("    " + nid + ' -->|"repeat"| ' + loop_nid)
            pending[:] = [(loop_nid, "exit")]
        else:
            pending[:] = [(nid, None)]

        # 5. Post-expression
        if post_expr:
            post_nid = add_node(
                "action", diagram_label(f"Post: {post_expr}", "PostExpr", max_length=64)
            )
            attach(post_nid)
            pending[:] = [(post_nid, None)]

    close_dangling_case()
    while stack:
        frame = stack.pop()
        if frame["kind"] == "switch":
            pending[:] = list(frame["case_tails"]) + list(pending)
        elif frame["kind"] == "if":
            tails = list(frame["tails"]) + list(pending)
            if frame.get("open_no"):
                tails.append((frame["open_no"], "no"))
            pending[:] = tails
        elif frame["kind"] == "loop":
            pending[:] = [(frame["header"], "exit"), *frame.get("break_tails", [])]

    needs_end = any(label for _, label in pending) or len(pending) > 1
    if needs_end:
        end_nid = add_node("action", "End")
        for source, label in pending:
            if label:
                edge_lines.append(f'    {source} -->|"{diagram_label(label, "")}"| {end_nid}')
            else:
                edge_lines.append(f"    {source} --> {end_nid}")

    # Add goto branching edges
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = step.get("id")
        if not step_id:
            continue
        nid = nid_by_step_id.get(step_id)
        if not nid:
            continue
        exprs = step.get("expressions") or {}

        for act_key, tgt_key, lbl in [
            ("pass_action", "pass_action_target_id", "Pass"),
            ("fail_action", "fail_action_target_id", "Fail"),
            ("custom_true_action", "custom_true_target_id", "True"),
            ("custom_false_action", "custom_false_target_id", "False"),
        ]:
            if exprs.get(act_key) in ("GotoStep", "JumpToStep"):
                tgt_id_raw = exprs.get(tgt_key, "").strip().strip('"')
                if tgt_id_raw in nid_by_step_id:
                    edge_lines.append(f'    {nid} -.->|"{lbl}"| {nid_by_step_id[tgt_id_raw]}')

    if not node_lines:
        return ""
    return "\n".join(["flowchart TD", *_CLASS_DEFS, *node_lines, *edge_lines, *click_lines])
