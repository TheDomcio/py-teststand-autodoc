from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_action(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    exprs: dict[str, str] = {}

    if step_type in ("Statement",):
        expr = get_ts_string(step_property_object, "TS.SData.Expr")
        if expr:
            exprs["expression"] = expr

    # SequenceCall targets are currently extracted directly in build_step_data since they
    # form top-level attributes rather than 'expressions' or 'step_settings',
    # but any internal expression parsing would go here.

    return exprs, {}
