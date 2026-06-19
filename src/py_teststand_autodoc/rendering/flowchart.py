"""Build styled Mermaid control-flow diagram from sequencer step group.

Reconstructs NI flow-control markers (If/ElseIf/Else, Select/Case, loops,
Break/Continue, End) into Mermaid flowchart. Decisions as diamonds, loops
with back edges, SequenceCall as subroutines, other steps as boxes.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

# NI flow-control step type names (Sequencer built-in step types).
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
]

_SHAPE_CLASS = {
    "decision": "decision",
    "loop": "loop",
    "call": "seqcall",
    "jump": "jump",
    "box": "action",
    "popup": "popup",
    "timer": "timer",
}


def diagram_label(text: str, fallback: str, max_length: int = 48) -> str:
    """Short, quote-safe label for Mermaid node or edge."""
    label = (text or "").strip() or fallback
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


def build_flowchart(steps: list[dict[str, Any]], detailed_popup_messages: bool = False) -> str:
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

    def new_id() -> str:
        counter["n"] += 1
        return "n" + str(counter["n"])

    def add_node(shape: str, label: str, step: dict[str, Any] | str = "") -> str:
        nid = new_id()
        step_name = ""
        step_id = ""
        if isinstance(step, dict):
            step_name = step.get("name", "")
            step_id = step.get("id") or ""
        else:
            step_name = step

        # Pop the next position for this name and look up its index.
        pos_queue = name_positions.get(step_name)
        if pos_queue:
            pos = pos_queue.popleft()
            idx = exec_idx_by_pos.get(pos)
            if idx is not None:
                label = f"[{idx}] {label}"
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

        # Add link to anchor in Markdown using Step's unique ID
        if step_id:
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
            nid = add_node("jump", diagram_label(name, step_type.split("_")[-1]), step)
            attach(nid)
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

            label = f"**{name}**"
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
                label += f"<br/>*(Default: {default_btn})*"

            if timeout and timeout not in ("0", "0.0"):
                wait_text = f"Timeout: {timeout}s"
                if timer_btn:
                    wait_text += f" → triggers [{timer_btn}]"
                label += f"<br/>**{wait_text}**"

            nid = add_node("popup", diagram_label(label, "Popup", max_length=256), step)
            attach(nid)
            pending[:] = [(nid, None)]
            continue

        # Wait steps: UML timer symbol with normalized duration
        if step_type in ("NI_Wait", "Wait"):
            exprs = step.get("expressions", {})
            raw_time = exprs.get("time_to_wait") or exprs.get("expression") or ""
            wait_label = _normalize_wait(raw_time) if raw_time else name
            nid = add_node("timer", diagram_label(f"⏱ {wait_label}", "Wait"), step)
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

        shape = "box"
        nid = add_node(shape, diagram_label(name, step_type or "Step"), step)
        attach(nid)
        pending[:] = [(nid, None)]

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

    if not node_lines:
        return ""
    return "\n".join(["flowchart TD", *_CLASS_DEFS, *node_lines, *edge_lines, *click_lines])
