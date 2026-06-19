from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_looping_properties(step_property_object: Any) -> dict[str, str]:
    """Extract TS looping configuration like LoopType and LoopWhile."""
    exprs: dict[str, str] = {}
    loop_type = get_ts_string(step_property_object, "TS.LoopType")
    if loop_type and loop_type not in ("0", "", "NoLooping"):
        exprs["loop_type"] = loop_type
        loop_while = get_ts_string(step_property_object, "TS.LoopWhile")
        if loop_while:
            exprs["loop_while"] = loop_while
        loop_init = get_ts_string(step_property_object, "TS.LoopInitialize")
        if loop_init:
            exprs["loop_init"] = loop_init
        loop_inc = get_ts_string(step_property_object, "TS.LoopIncrement")
        if loop_inc:
            exprs["loop_increment"] = loop_inc

    return exprs
