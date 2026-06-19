from __future__ import annotations

from typing import Any

from ..utils import get_ts_string


def extract_infrastructure(
    step_type: str,
    step_property_object: Any,
) -> tuple[dict[str, str], dict[str, str]]:
    configs: dict[str, str] = {}

    if step_type == "NI_PropertyLoader":
        source_path = get_ts_string(
            step_property_object,
            "TS.SData.SourceLocation.FileLocation.FilePath",
        )
        if source_path:
            configs["Source Path"] = source_path

        db_conn = get_ts_string(
            step_property_object,
            "TS.SData.SourceLocation.DatabaseLocation.ConnectionString",
        )
        if db_conn:
            configs["Database Connection"] = db_conn

    return {}, configs
