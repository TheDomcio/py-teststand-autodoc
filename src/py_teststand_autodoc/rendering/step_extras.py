"""Detailed step configuration formatting."""

from __future__ import annotations

from typing import Any

from .markdown.text import code_span, sanitize

_ACTION_LABELS = {
    # COM string values
    "Next": "Continue",
    "JumpToStep": "Jump to Step",
    "ReturnFromSequence": "Return from Sequence",
    "TerminateExecution": "Terminate Execution",
    "TerminateExecutionWithError": "Terminate Execution with Error",
    "Break": "Break",
    "ContinueLoop": "Continue Loop",
    "JumpToSequence": "Jump to Sequence",
    # Legacy integer string values
    "1": "Continue",
    "2": "Jump to Step",
    "3": "Return from Sequence",
    "4": "Terminate Execution",
    "5": "Terminate Execution with Error",
    "6": "Break",
    "7": "Continue Loop",
    "8": "Jump to Sequence",
}


def _get_action_name(code: str) -> str:
    return _ACTION_LABELS.get(code, f"Action({code})")


def append_step_extras(md: list[str], step: dict[str, Any], indent: str = "    ") -> None:
    """Render per-step detail block: full expressions, loops, routing, params."""
    exprs = step.get("expressions") or {}
    params = step.get("module_parameters") or []
    reqs = step.get("requirements") or []
    settings = step.get("step_settings") or {}
    record_res = exprs.get("record_result", "")
    mutex = exprs.get("mutex", "")
    if not any([exprs, params, settings, reqs, record_res, mutex]):
        return

    step_type = step.get("type", "")

    lines: list[str] = []

    # MessagePopup details are shown in the flowchart - skip detailed block
    if step_type == "MessagePopup":
        return
    if exprs.get("expression"):
        lines.append("**Expression**: " + code_span(exprs["expression"]))

    if exprs.get("pre_expr"):
        lines.append("**Pre-expression**: " + code_span(exprs["pre_expr"]))
    if exprs.get("post_expr"):
        lines.append("**Post-expression**: " + code_span(exprs["post_expr"]))

    # Custom status/condition
    if exprs.get("custom_condition"):
        lines.append("**Custom condition**: " + code_span(exprs["custom_condition"]))
        if exprs.get("custom_true_action"):
            tgt = exprs.get("custom_true_target", "")
            act = _get_action_name(exprs["custom_true_action"])
            suffix = f" → {code_span(tgt)}" if tgt else ""
            lines.append(f"**If true**: {act}{suffix}")
        if exprs.get("custom_false_action"):
            tgt = exprs.get("custom_false_target", "")
            act = _get_action_name(exprs["custom_false_action"])
            suffix = f" → {code_span(tgt)}" if tgt else ""
            lines.append(f"**If false**: {act}{suffix}")

    # Loop info
    if exprs.get("loop_type"):
        _loop_labels = {
            "FixedNumLoops": "Fixed count",
            "PassFailCount": "Pass/fail count",
            "Custom": "Custom",
        }
        loop_label = _loop_labels.get(exprs["loop_type"], exprs["loop_type"])
        parts = [f"**Loop**: {loop_label}"]
        if exprs.get("loop_while"):
            parts[0] += " " + code_span(exprs["loop_while"])
        if exprs.get("loop_init"):
            parts.append("**Loop init**: " + code_span(exprs["loop_init"]))
        if exprs.get("loop_increment"):
            parts.append("**Loop increment**: " + code_span(exprs["loop_increment"]))
        lines.extend(parts)

    # Routing
    if exprs.get("pass_action"):
        target = exprs.get("pass_action_target", "")
        action = _get_action_name(exprs["pass_action"])
        arrow = f" → {code_span(target)}" if target else ""
        lines.append(f"**On pass**: {action}{arrow}")
    if exprs.get("fail_action"):
        target = exprs.get("fail_action_target", "")
        action = _get_action_name(exprs["fail_action"])
        arrow = f" → {code_span(target)}" if target else ""
        lines.append(f"**On fail**: {action}{arrow}")

    # Step Settings (Algorithmic Configs)
    if settings:
        for k, v in settings.items():
            lines.append(f"**{k}**: {code_span(v)}")

    # Synchronization
    if mutex:
        lines.append(f"**Mutex Lock**: {code_span(mutex)}")

    # Result Recording
    if record_res:
        lines.append(f"**Record Result**: {code_span(record_res)}")

    # Requirements
    if reqs:
        lines.append("**Requirements**: " + ", ".join(code_span(r) for r in reqs))

    # Module parameters
    if params:
        lines.append("**Parameters**:")
        for p in params:
            p_name = sanitize(p.get("name", ""))
            p_type = sanitize(p.get("type", ""))
            lines.append(f"- `{p_name}` — {p_type}")

    if not lines:
        return

    for line in lines:
        if line.startswith("- "):
            md.append(indent + "    " + line)
        else:
            md.append(indent + "- " + line)
