from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_advanced_properties(
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    """Extract advanced step properties like LoadOpt, UnloadOpt, and ReportText.

    Returns:
        (expressions, settings)
    """
    exprs: dict[str, str] = {}
    configs: dict[str, str] = {}

    # Load/Unload Options
    try:
        if step_property_object.exists("TS.LoadOpt"):
            load_opt = step_property_object.get_val_string("TS.LoadOpt", 0)
            if load_opt and load_opt not in (
                "PreloadWhenOpened",
                "PreloadWhenExecuted",
                "PreloadWithSequence",
            ):
                configs["Load Option"] = load_opt
    except Exception:
        pass

    try:
        if step_property_object.exists("TS.UnloadOpt"):
            unload_opt = step_property_object.get_val_string("TS.UnloadOpt", 0)
            if unload_opt and unload_opt not in (
                "UnloadWhenClosed",
                "UnloadWithFile",
                "UnloadWithSequence",
            ):
                configs["Unload Option"] = unload_opt
    except Exception:
        pass

    # Report Text
    try:
        if step_property_object.exists("Result.ReportText"):
            report_text = get_ts_string(step_property_object, "Result.ReportText")
            if report_text:
                exprs["report_text"] = report_text
    except Exception:
        pass

    # Icon extraction removed per user request

    # Run Mode (Skip, ForcePass, ForceFail)
    try:
        if step_property_object.exists("TS.RunMode"):
            run_mode = get_ts_string(step_property_object, "TS.RunMode")
            if run_mode and run_mode != "Normal":
                configs["RunMode"] = run_mode
    except Exception:
        pass

    return exprs, configs
