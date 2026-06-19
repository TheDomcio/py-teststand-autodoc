"""Detect steps that rename themselves at run time.

Step displayed name static unless expression assigns to Step.Name.
When happens, name in editor is template; documentation tags (Dynamic).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_teststand import Step

# Matches an assignment to a `...Step.Name` property in an expression.
_STEP_NAME_ASSIGNMENT = re.compile(r"Step\s*\.\s*Name\s*=", re.IGNORECASE)

_EXPRESSION_ATTRIBUTES = ("pre_expression", "post_expression", "status_expression")


def has_dynamic_name(step: Step) -> bool:
    """True if any expression assigns to Step.Name."""
    for attribute in _EXPRESSION_ATTRIBUTES:
        try:
            expression = getattr(step, attribute, "") or ""
        except Exception:
            continue
        if _STEP_NAME_ASSIGNMENT.search(str(expression)):
            return True
    return False
