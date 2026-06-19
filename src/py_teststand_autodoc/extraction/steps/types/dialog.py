from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_dialog(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    exprs: dict[str, str] = {}
    if step_type == "MessagePopup":
        for key, field in (
            ("title", "TitleExpr"),
            ("message", "MessageExpr"),
            ("button1", "Button1Label"),
            ("button2", "Button2Label"),
            ("button3", "Button3Label"),
            ("button4", "Button4Label"),
            ("button5", "Button5Label"),
            ("button6", "Button6Label"),
        ):
            val = get_ts_string(step_property_object, field)
            if val:
                exprs[key] = val

        for key, field in (
            ("timer_button", "TimerButton"),
            ("default_button", "DefaultButton"),
            ("time_to_wait", "TimeToWait"),
        ):
            try:
                num = step_property_object.get_val_number(field, 0)
                exprs[key] = str(int(num)) if num.is_integer() else str(num)
            except Exception:
                try:
                    exprs[key] = step_property_object.get_val_string(field, 0)
                except Exception:
                    pass
    return exprs, {}
