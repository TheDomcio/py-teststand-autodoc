"""Step extraction helpers for building step dicts."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..constants import PropertyPath
from .criteria import get_limits, get_multiple_numeric_measurements
from .module_info import normalize_adapter
from .step_naming import has_dynamic_name
from .steps.properties import extract_universal_properties
from .steps.types import extract_type_specific_properties
from .steps.utils import get_call_property

if TYPE_CHECKING:
    from py_teststand import Step

logger = logging.getLogger(__name__)


def clean_step_description(desc: str, _step_type: str, vi_path: str = "") -> str:
    if not desc:
        return ""

    desc_strip = desc.replace("  ", " ").strip()

    # Strip VI name/path if present
    if vi_path:
        vi_name = Path(vi_path).name
        if vi_name:
            desc_strip = re.sub(r",\s*" + re.escape(vi_name), "", desc_strip, flags=re.IGNORECASE)
            desc_strip = re.sub(re.escape(vi_name), "", desc_strip, flags=re.IGNORECASE)
            desc_strip = desc_strip.strip(", ")

    desc_lower = desc_strip.lower()

    # Check if the description is default/generic
    generics = [
        "pass/fail test",
        "numeric limit test",
        "string value test",
        "multiple numeric limit test",
        "action",
        "sequence call",
        "message popup",
        "wait",
        "label",
    ]

    # If description is a generic name or starts with it (auto-generated)
    if any(desc_lower.startswith(g) for g in generics) or desc_lower in generics:
        return ""

    return desc_strip


def get_step_comment(step: Step) -> str:
    """Safely get step comment via raw IPropertyObject interface."""
    try:
        po = step.as_property_object()
        comment = po._com_obj.Comment
        if comment:
            return comment.strip()
    except Exception as e:
        logger.debug(f"Could not read step comment: {e}")
    return ""


def get_step_precondition(step_property_object: Any) -> str:
    """Safely get step precondition expression."""
    try:
        if step_property_object.exists("TS.Precond"):
            return step_property_object.get_val_string("TS.Precond", 0)
    except Exception as e:
        logger.debug(f"Could not read step precondition: {e}")
    return ""


def get_step_description(step: Step) -> str:
    """Safely get step description."""
    try:
        desc = step.description
        # Skip descriptions that are just NameOf(Step) expressions
        if re.match(r"^NameOf\s*\(", desc, re.IGNORECASE):
            return ""
        return desc
    except Exception as e:
        logger.debug(f"Could not read step description: {e}")
        return ""


def build_step_data(
    step: Step,
    step_property_object: Any,
    module_info: dict[str, Any] | None,
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    """Build dict of step data for formatting."""
    normalized_adapter = normalize_adapter(step.adapter_key_name)
    vi_path = ""
    if normalized_adapter == "LabVIEW" and module_info:
        vi_path = module_info.get("path") or ""

    clean_desc = get_step_description(step)
    clean_desc = clean_step_description(clean_desc, step.step_type_name, vi_path)

    precond = get_step_precondition(step_property_object)
    precond = re.sub(r'\[?"ID#:[a-zA-Z0-9+/]+"\]?', '"Step"', precond)

    name = step.name.strip()
    # If name is a TestStand expression (like NameOf(Step)), use step type instead
    if re.match(r"^NameOf\s*\(", name, re.IGNORECASE):
        name = step.step_type_name
    elif has_dynamic_name(step):
        name = name + " (Dynamic)"

    step_id = ""
    try:
        step_id = step.unique_step_id
    except Exception as e:
        logger.debug(f"Could not read unique_step_id: {e}")

    step_type = step.step_type_name
    step_data: dict[str, Any] = {
        "id": step_id,
        "name": name,
        "type": step_type,
        "adapter": normalized_adapter,
        "description": clean_desc,
        "comment": get_step_comment(step),
        "module": module_info["path"] if (module_info and module_info.get("path")) else "",
        "limits": get_limits(step),
        "precondition": precond.strip(),
        "expressions": {},
        "skipped": skipped,
    }

    try:
        step_data["logic"] = {
            "pre_expression": getattr(step, "pre_expression", "").strip(),
            "post_expression": getattr(step, "post_expression", "").strip(),
            "status_expression": getattr(step, "status_expression", "").strip(),
            "loop_type": getattr(step, "loop_type", 0),
        }
    except Exception as e:
        logger.debug(f"Could not read logic properties: {e}")

    if module_info and module_info.get("parameters"):
        step_data["module_parameters"] = module_info["parameters"]

    if module_info and module_info.get("extra"):
        step_data["module_info"] = {"extra": module_info["extra"]}

    # 1. Extract Universal Domain Properties
    univ_exprs, univ_configs, reqs = extract_universal_properties(step_property_object)

    step_data["expressions"].update(univ_exprs)
    configs = univ_configs
    if reqs:
        step_data["requirements"] = reqs

    # 2. Extract Step-Type Specific Domain Properties
    type_exprs, type_configs = extract_type_specific_properties(step_type, step_property_object)

    step_data["expressions"].update(type_exprs)
    configs.update(type_configs)

    # Wait properties can be generic enough that they affect top-level estimation
    if step_type in ("NI_Wait", "Wait"):
        expr = step_data["expressions"].get("expression", "")
        if expr:
            # Extract numeric value from TimeInterval(.25) or similar
            match = re.search(r"TimeInterval\s*\(\s*([\d.]+)\s*\)", expr, re.IGNORECASE)
            if match:
                try:
                    step_data["estimated_delay"] = float(match.group(1))
                except ValueError as e:
                    logger.debug(f"Could not parse wait delay {match.group(1)!r}: {e}")
                    step_data["estimated_delay"] = 0.0
            else:
                # Try direct numeric parse
                try:
                    step_data["estimated_delay"] = float(expr)
                except ValueError:
                    # Dynamic variable or expression - treat as 0 for estimation
                    logger.debug(f"Dynamic wait expression, treating as 0: {expr!r}")
                    step_data["estimated_delay"] = 0.0

    configs = {k: v for k, v in configs.items() if v}
    if configs:
        step_data["step_settings"] = configs

    if step_type == "SequenceCall":
        step_data["target_sequence"] = get_call_property(
            step_property_object,
            PropertyPath.TARGET_SEQUENCE,
            PropertyPath.TARGET_SEQUENCE_EXPR,
        )

    if normalized_adapter == "LabVIEW" and vi_path:
        step_data["vi"] = vi_path

    return step_data


def expand_multiple_numeric_step(
    step: Step,
    step_property_object: Any,
    module_info: dict[str, Any] | None,
    *,
    skipped: bool = False,
) -> list[dict[str, Any]]:
    """Expand NI_MultipleNumericLimitTest into per-measurement steps.

    Returns list of step dicts with [0], [1] prefix in name.
    """
    measurements = get_multiple_numeric_measurements(step)
    if not measurements:
        return [build_step_data(step, step_property_object, module_info, skipped=skipped)]

    base_data = build_step_data(step, step_property_object, module_info, skipped=skipped)
    base_name = base_data["name"]
    results = []
    for i, m in enumerate(measurements):
        step_copy = dict(base_data)
        step_copy["name"] = f"{base_name} [{i}]"
        if base_data.get("id"):
            step_copy["id"] = f"{base_data['id']}_{i}"
        step_copy["limits"] = {
            "low": m["low"],
            "high": m["high"],
            "target": m["target"],
            "unit": m["unit"],
        }
        step_copy["measurement_name"] = m["name"]
        results.append(step_copy)
    return results
