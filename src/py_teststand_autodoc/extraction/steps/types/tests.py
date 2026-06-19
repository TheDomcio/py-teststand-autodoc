from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_tests(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    configs: dict[str, str] = {}
    if step_type == "StringValueTest":
        ignore_case = get_ts_string(step_property_object, "TS.SData.IgnoreCase")
        if ignore_case:
            configs["Ignore Case"] = ignore_case
    return {}, configs
