from __future__ import annotations

from typing import Any

from .action import extract_action
from .dialog import extract_dialog
from .flow_control import extract_flow_control
from .infrastructure import extract_infrastructure
from .tests import extract_tests

# Map step types to their specific domain extractors
STEP_EXTRACTORS = {
    # Tests Domain
    "StringValueTest": extract_tests,
    "NumericLimitTest": extract_tests,
    "PassFailTest": extract_tests,
    "NI_MultipleNumericLimitTest": extract_tests,
    # Dialog Domain
    "MessagePopup": extract_dialog,
    # Flow Control Domain
    "NI_Wait": extract_flow_control,
    "Wait": extract_flow_control,
    "NI_Flow_If": extract_flow_control,
    "NI_Flow_ElseIf": extract_flow_control,
    "NI_Flow_Select": extract_flow_control,
    # Action Domain
    "Statement": extract_action,
    "SequenceCall": extract_action,
    # Infrastructure Domain
    "NI_PropertyLoader": extract_infrastructure,
}


def extract_type_specific_properties(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    """Extract step-specific expressions and settings based on step type domains.

    Returns:
        (expressions, settings)

    """
    if step_type in STEP_EXTRACTORS:
        return STEP_EXTRACTORS[step_type](step_type, step_property_object)
    return {}, {}
