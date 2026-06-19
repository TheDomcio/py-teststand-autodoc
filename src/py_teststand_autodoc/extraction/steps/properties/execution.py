from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_execution_properties(
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Extract Mutex, Result Recording, Requirements, and Call Arguments.

    Returns:
        (expressions, settings, requirements)

    """
    exprs: dict[str, str] = {}
    configs: dict[str, str] = {}
    reqs: list[str] = []

    # Synchronization (Mutex)
    try:
        if step_property_object.exists("TS.UseMutex"):
            use_mutex = step_property_object.get_val_string("TS.UseMutex", 0)
            if use_mutex and use_mutex.lower() == "true":
                mutex_name = step_property_object.get_val_string("TS.MutexNameOrRef", 0)
                if mutex_name:
                    exprs["mutex"] = mutex_name
    except Exception:
        pass

    # Result Recording
    try:
        if step_property_object.exists("TS.ResultOption"):
            res_opt = step_property_object.get_val_string("TS.ResultOption", 0)
            if res_opt and res_opt.lower() != "true":
                exprs["record_result"] = res_opt
    except Exception:
        pass

    # Requirements
    try:
        if step_property_object.exists("TS.Requirements.Links"):
            links = step_property_object.get_property_object("TS.Requirements.Links", 0)
            n = links.get_num_elements()
            for i in range(n):
                sub = links.get_property_object_by_index("", 0, i)
                if sub.exists("Requirement"):
                    req_val = sub.get_val_string("Requirement", 0)
                    if req_val:
                        reqs.append(req_val)
    except Exception:
        pass

    # Generic executable Call arguments
    cmd = get_ts_string(step_property_object, "TS.SData.Call.CmdLine")
    if cmd:
        configs["Command Line"] = cmd
    args = get_ts_string(step_property_object, "TS.SData.Call.ArgString")
    if args:
        configs["Arguments"] = args

    return exprs, configs, reqs
