"""Extract structured test limits from sequencer steps.

Value types:
- Numeric: Low/High bound with unit.
- Boolean: target always True; unit "boolean".
- String: expected text is target; unit "Text".
- Non-test steps: no limits.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..constants import PropertyPath

if TYPE_CHECKING:
    from py_teststand import Step

logger = logging.getLogger(__name__)

# Comparison types that use two numeric bounds (Low and High).
_RANGE_COMPARISONS = {"GELE", "GELT", "GTLE", "GTLT"}
# Comparison types that use a single lower / upper bound.
_LOWER_BOUND_COMPARISONS = {"GE", "GT"}
_UPPER_BOUND_COMPARISONS = {"LE", "LT"}
# Legacy integer comparison codes mapped to range semantics.
_LEGACY_RANGE_CODES = {"7", "8"}


def _empty_limits() -> dict[str, str]:
    return {"low": "", "high": "", "target": "", "unit": "", "comp": ""}


def _format_value(value: object) -> str:
    """Render limit value, drop trailing .0 on whole numbers."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _read_unit(property_object: Any) -> str:
    for path in (PropertyPath.RESULT_UNITS, "Limits.Units", PropertyPath.UNITS):
        if property_object.exists(path):
            unit = property_object.get_val_string(path, 0)
            if unit:
                return unit
    return ""


def _string_limits(property_object: Any, unit: str) -> dict[str, str]:
    limits = _empty_limits()
    expected = ""
    if property_object.exists(PropertyPath.LIMITS_STRING):
        expected = property_object.get_val_string(PropertyPath.LIMITS_STRING, 0)
    limits["low"] = limits["high"] = limits["target"] = expected
    limits["unit"] = unit or "Text"
    return limits


def _boolean_limits(unit: str) -> dict[str, str]:
    limits = _empty_limits()
    limits["target"] = "True"
    limits["unit"] = unit or "boolean"
    return limits


_COMP_CHARACTERS = {
    "EQ": "==",
    "1": "==",
    "NE": "!=",
    "2": "!=",
    "GT": ">",
    "3": ">",
    "GE": ">=",
    "4": ">=",
    "LT": "<",
    "5": "<",
    "LE": "<=",
    "6": "<=",
    "GELT": ">= x <",
    "7": ">= x <",
    "GELE": ">= x <=",
    "8": ">= x <=",
    "GTLT": "> x <",
    "GTLE": "> x <=",
}


def _numeric_limits(property_object: Any, unit: str) -> dict[str, str]:
    limits = _empty_limits()
    has_low = property_object.exists(PropertyPath.LIMITS_LOW)
    has_high = property_object.exists(PropertyPath.LIMITS_HIGH)
    low = (
        _format_value(property_object.get_val_variant(PropertyPath.LIMITS_LOW, 0))
        if has_low
        else ""
    )
    high = (
        _format_value(property_object.get_val_variant(PropertyPath.LIMITS_HIGH, 0))
        if has_high
        else ""
    )
    comparison = ""
    if property_object.exists(PropertyPath.COMP):
        comparison = str(property_object.get_val_variant(PropertyPath.COMP, 0)).strip().upper()

    limits["comp"] = _COMP_CHARACTERS.get(comparison, comparison)

    if comparison in _RANGE_COMPARISONS or comparison in _LEGACY_RANGE_CODES:
        limits["low"], limits["high"] = low, high
    elif comparison in _LOWER_BOUND_COMPARISONS:
        limits["low"] = low
    elif comparison in _UPPER_BOUND_COMPARISONS:
        limits["high"] = high or low
    elif comparison == "EQ":
        limits["target"] = low or high
    elif comparison == "NE":
        limits["target"] = "!= " + (low or high)
    else:
        limits["low"], limits["high"] = low, high
    limits["unit"] = unit
    return limits


def get_limits(step: Step) -> dict[str, str]:
    """Return {low, high, target, unit} dict for step's test limits."""
    type_name = step.step_type_name
    type_lower = type_name.lower()
    if "test" not in type_lower:
        return _empty_limits()

    try:
        property_object = step.as_property_object()
        unit = _read_unit(property_object)

        if "passfail" in type_lower:
            return _boolean_limits(unit)
        if "stringvalue" in type_lower:
            return _string_limits(property_object, unit)
        if "multiplenumeric" in type_lower:
            return _empty_limits()
        if "numericlimit" in type_lower:
            return _numeric_limits(property_object, unit)

        # Unknown test type: probe the available limit properties.
        if property_object.exists(PropertyPath.LIMITS_STRING):
            return _string_limits(property_object, unit)
        if property_object.exists(PropertyPath.LIMITS_LOW) or property_object.exists(
            PropertyPath.LIMITS_HIGH,
        ):
            return _numeric_limits(property_object, unit)
        return _boolean_limits(unit)
    except Exception as e:
        logger.debug(f"Could not extract limits for step {step.name}: {e}")
        return _empty_limits()


def get_multiple_numeric_measurements(step: Step) -> list[dict[str, str]]:
    """Extract per-measurement limits from NI_MultipleNumericLimitTest step.

    Returns list of {name, low, high, target, unit} dicts.
    """
    try:
        property_object = step.as_property_object()
        # Measurement array is under Result.Measurement
        if not hasattr(property_object, "Result"):
            return []
        result = property_object.Result
        if result is None or not hasattr(result, "Measurement"):
            return []
        measurement_array = result.Measurement
        if measurement_array is None:
            return []

        num = measurement_array.get_num_elements()
        results = []
        for i in range(num):
            m = measurement_array.get_property_object_by_offset(i, 0)
            if m is None:
                continue
            name = m.name if hasattr(m, "name") else f"[{i}]"
            # Each measurement has Limits inside it
            if not hasattr(m, "Limits"):
                continue
            limits_obj = m.Limits
            if limits_obj is None:
                continue
            unit = _read_unit(m)
            # Read Low and High from the Limits sub-object
            low = ""
            high = ""
            if hasattr(limits_obj, "Low"):
                low = _format_value(limits_obj.Low)
            if hasattr(limits_obj, "High"):
                high = _format_value(limits_obj.High)
            results.append({"name": name, "low": low, "high": high, "target": "", "unit": unit})
        return results
    except Exception as e:
        logger.debug(f"Could not extract multiple numeric measurements: {e}")
        return []
