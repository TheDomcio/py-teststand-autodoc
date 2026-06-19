from __future__ import annotations

from typing import Any

from .execution import extract_execution_properties
from .looping import extract_looping_properties
from .routing import extract_routing_properties


def extract_universal_properties(
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Extract all universal properties that apply to any step type.

    Returns:
        (expressions, settings, requirements)

    """
    exprs: dict[str, str] = {}
    configs: dict[str, str] = {}
    reqs: list[str] = []

    # Routing (Pre/Post, Status, Pass/Fail)
    exprs.update(extract_routing_properties(step_property_object))

    # Looping
    exprs.update(extract_looping_properties(step_property_object))

    # Execution (Mutex, Record Result, Call Args)
    exec_exprs, exec_configs, exec_reqs = extract_execution_properties(step_property_object)
    exprs.update(exec_exprs)
    configs.update(exec_configs)
    reqs.extend(exec_reqs)

    return exprs, configs, reqs
