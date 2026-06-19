"""Helpers for serializing PropertyObjects."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_teststand import PropertyObject

_RESULT_LIST = "ResultList"


def serialize_property_object(property_object: PropertyObject) -> list[dict[str, str]]:
    """Serialize PropertyObject into list of {name, type} pairs.

    Handles standard containers and DLL/CVI parameter arrays.
    """
    vars_list: list[dict[str, str]] = []

    if property_object.is_array:
        # DLL/CVI Parms array
        try:
            num_elements = property_object.get_num_elements()
            for i in range(num_elements):
                elem = property_object.get_property_object_by_offset(i, 0)
                if not elem:
                    continue
                try:
                    # DLL/CVI parameters store the name in "Name" and the mapping in "ArgVal"
                    name = elem.get_val_string("Name", 0)
                    val = elem.get_val_string("ArgVal", 0)
                    if not val:
                        val = elem.get_type_display_string("")
                    vars_list.append({"name": name.strip(), "type": val.strip()})
                except Exception:
                    # Fallback for unexpected array types
                    vars_list.append({"name": f"[{i}]", "type": elem.get_type_display_string("")})
            return vars_list
        except Exception:
            return []

    # Standard container
    try:
        count = property_object.get_num_sub_properties("")
        for i in range(count):
            name = property_object.get_nth_sub_property_name("", i)
            if name == _RESULT_LIST:
                continue

            v_type = property_object.get_type_display_string(name)
            vars_list.append({"name": name.strip(), "type": v_type.strip()})
    except Exception:
        pass

    return vars_list
