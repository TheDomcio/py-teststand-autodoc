"""Detailed step configuration formatting."""

from __future__ import annotations

from typing import Any

from .markdown.text import code_block, code_span, sanitize

_ACTION_LABELS = {
    "Next": "Continue",
    "JumpToStep": "Jump to Step",
    "ReturnFromSequence": "Return from Sequence",
    "TerminateExecution": "Terminate Execution",
    "TerminateExecutionWithError": "Terminate Execution with Error",
    "Break": "Break",
    "ContinueLoop": "Continue Loop",
    "JumpToSequence": "Jump to Sequence",
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


def _code_block_inside_admonition(label: str, code: str, base_indent: str) -> list[str]:
    ci = base_indent + "    "
    lines: list[str] = []
    lines.append(ci + f"- **{label}**:")
    lines.append("")
    lines.append(code_block(code, indent=len(ci + "  ")))
    lines.append("")
    return lines


def append_step_extras(md: list[str], step: dict[str, Any], indent: str = "    ") -> None:
    exprs = step.get("expressions") or {}
    params = step.get("module_parameters") or []
    reqs = step.get("requirements") or []
    settings = step.get("step_settings") or {}
    record_res = exprs.get("record_result", "")
    mutex = exprs.get("mutex", "")
    if not any([exprs, params, settings, reqs, record_res, mutex]):
        return

    if step.get("type") == "MessagePopup":
        return

    ci = indent + "    "
    item = ci + "- "
    out: list[str] = []

    if exprs.get("expression"):
        out.extend(_code_block_inside_admonition("Expression", exprs["expression"], indent))
    if exprs.get("pre_expr"):
        out.extend(_code_block_inside_admonition("Pre-expression", exprs["pre_expr"], indent))
    if exprs.get("post_expr"):
        out.extend(_code_block_inside_admonition("Post-expression", exprs["post_expr"], indent))

    if exprs.get("custom_condition"):
        cond = exprs["custom_condition"]
        out.extend(_code_block_inside_admonition("Custom condition", cond, indent))
        if exprs.get("custom_true_action"):
            tgt = exprs.get("custom_true_target", "")
            act = _get_action_name(exprs["custom_true_action"])
            suffix = f" \u2192 {code_span(tgt)}" if tgt else ""
            out.append(item + f"**If true**: {act}{suffix}")
        if exprs.get("custom_false_action"):
            tgt = exprs.get("custom_false_target", "")
            act = _get_action_name(exprs["custom_false_action"])
            suffix = f" \u2192 {code_span(tgt)}" if tgt else ""
            out.append(item + f"**If false**: {act}{suffix}")

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
            parts.append(item + "**Loop init**: " + code_span(exprs["loop_init"]))
        if exprs.get("loop_increment"):
            parts.append(item + "**Loop increment**: " + code_span(exprs["loop_increment"]))
        out.extend(parts)

    if exprs.get("pass_action"):
        target = exprs.get("pass_action_target", "")
        action = _get_action_name(exprs["pass_action"])
        arrow = f" \u2192 {code_span(target)}" if target else ""
        out.append(item + f"**On pass**: {action}{arrow}")
    if exprs.get("fail_action"):
        target = exprs.get("fail_action_target", "")
        action = _get_action_name(exprs["fail_action"])
        arrow = f" \u2192 {code_span(target)}" if target else ""
        out.append(item + f"**On fail**: {action}{arrow}")

    if settings:
        for k, v in settings.items():
            out.append(item + f"**{k}**: {code_span(v)}")

    if mutex:
        out.append(item + f"**Mutex Lock**: {code_span(mutex)}")

    if record_res:
        out.append(item + f"**Record Result**: {code_span(record_res)}")

    if reqs:
        out.append(item + "**Requirements**: " + ", ".join(code_span(r) for r in reqs))

    if params:
        out.append(item + "**Parameters**:")
        for p in params:
            p_name = sanitize(p.get("name", ""))
            p_type = sanitize(p.get("type", ""))
            out.append(ci + f"    - `{p_name}` \u2014 {p_type}")

    if not out:
        return

    md.append("")
    md.append(indent + '!!! info "Step Configuration"')
    md.extend(out)
    md.append("")
