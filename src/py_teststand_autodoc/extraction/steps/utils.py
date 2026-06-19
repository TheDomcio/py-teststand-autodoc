from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# A TestStand expression that is just a quoted string constant, e.g. "RF Test".
_STRING_LITERAL = re.compile(r'^"([^"]*)"$')


def _expression_literal(expression: str) -> str:
    """Plain string inside expression literal like "RF Test". Dynamic expressions unchanged."""
    match = _STRING_LITERAL.match(expression.strip())
    return match.group(1) if match else expression.strip()


def get_call_property(step_property_object: Any, plain: str, expr: str) -> str:
    """SequenceCall target property from plain or expression form."""
    try:
        if step_property_object.exists(plain):
            value = step_property_object.get_val_string(plain, 0)
            if value:
                return value
        if step_property_object.exists(expr):
            return _expression_literal(step_property_object.get_val_string(expr, 0))
    except Exception as e:
        logger.debug(f"Could not read call property {plain}/{expr}: {e}")
    return ""


def get_ts_string(step_property_object: Any, prop: str) -> str:
    """Safely read single TS string property."""
    try:
        if step_property_object.exists(prop):
            return step_property_object.get_val_string(prop, 0) or ""
    except Exception as e:
        logger.debug(f"Could not read TS string property {prop}: {e}")
    return ""
