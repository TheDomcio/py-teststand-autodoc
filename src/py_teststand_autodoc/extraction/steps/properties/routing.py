from __future__ import annotations

import re
from typing import Any

from ..utils import get_ts_string

# SequenceCall steps use this boilerplate StatusExpr by default — not worth showing.
_SEQCALL_DEFAULT_STATUS_EXPRS: tuple[str, ...] = (
    "",
    '(Step.Result.Status == "Done" '
    "&& (Step.TS.SData.ThreadOpt == 0 "
    '|| Step.TS.SData.ThreadOpt == 3)) ? "Passed" '
    ": Step.Result.Status",
)


def extract_routing_properties(step_property_object: Any) -> dict[str, str]:
    """Extract pre/post expressions, status expressions, and pass/fail actions."""
    exprs: dict[str, str] = {}

    # Pre/Post expressions
    pre = get_ts_string(step_property_object, "TS.PreExpr")
    if pre:
        exprs["pre_expr"] = pre
    post = get_ts_string(step_property_object, "TS.PostExpr")
    if post:
        exprs["post_expr"] = post

    # Pass/fail routing actions
    pass_act = get_ts_string(step_property_object, "TS.PassAct")
    fail_act = get_ts_string(step_property_object, "TS.FailAct")
    if pass_act and pass_act not in ("0", "", "Next"):
        exprs["pass_action"] = pass_act
        target = get_ts_string(step_property_object, "TS.PassActTarget")
        if target:
            exprs["pass_action_target"] = re.sub(r'\[?"ID#:[a-zA-Z0-9+/]+"\]?', '"Step"', target)

    if fail_act and fail_act not in ("0", "", "Next"):
        exprs["fail_action"] = fail_act
        target = get_ts_string(step_property_object, "TS.FailActTarget")
        if target:
            exprs["fail_action_target"] = re.sub(r'\[?"ID#:[a-zA-Z0-9+/]+"\]?', '"Step"', target)

    # Custom status expression
    status_expr = get_ts_string(step_property_object, "TS.StatusExpr")
    if status_expr and status_expr not in _SEQCALL_DEFAULT_STATUS_EXPRS:
        exprs["status_expr"] = status_expr

    # Custom pass/fail condition
    cust_expr = get_ts_string(step_property_object, "TS.CustExpr")
    if cust_expr:
        exprs["custom_condition"] = cust_expr
        cust_true = get_ts_string(step_property_object, "TS.CustTrueAct")
        cust_false = get_ts_string(step_property_object, "TS.CustFalseAct")
        if cust_true and cust_true not in ("0", "", "Next"):
            exprs["custom_true_action"] = cust_true
            t = get_ts_string(step_property_object, "TS.CustTrueActTarget")
            if t:
                exprs["custom_true_target"] = re.sub(r'\[?"ID#:[a-zA-Z0-9+/]+"\]?', '"Step"', t)
        if cust_false and cust_false not in ("0", "", "Next"):
            exprs["custom_false_action"] = cust_false
            t = get_ts_string(step_property_object, "TS.CustFalseActTarget")
            if t:
                exprs["custom_false_target"] = re.sub(r'\[?"ID#:[a-zA-Z0-9+/]+"\]?', '"Step"', t)

    return exprs
