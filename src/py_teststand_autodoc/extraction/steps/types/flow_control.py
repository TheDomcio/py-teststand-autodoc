from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_flow_control(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    exprs: dict[str, str] = {}

    if step_type in ("NI_Wait", "Wait"):
        for prop in ("TimeExpr", "TS.SData.TimeExpr"):
            val = get_ts_string(step_property_object, prop)
            if val:
                exprs["expression"] = val
                break

    elif step_type in ("NI_Flow_If", "NI_Flow_ElseIf", "NI_Flow_Select"):
        for prop in ("TS.SData.Expr", "TS.SData.Condition", "Condition"):
            val = get_ts_string(step_property_object, prop)
            if val:
                exprs["expression"] = val
                break

    return exprs, {}
