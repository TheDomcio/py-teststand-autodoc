"""Helpers for extracting module info from sequence steps."""

from __future__ import annotations

import logging
from typing import Any

from py_teststand import Module

from ..constants import AdapterType, PropertyPath
from ..shared.property_serializer import serialize_property_object

logger = logging.getLogger(__name__)


def get_module_info(step: Any) -> dict[str, Any] | None:
    """Extract module info (path and type) for step."""
    adapter = step.adapter_key_name
    module: Module = step.module
    path = ""
    m_type = ""
    extra: dict[str, str] = {}

    try:
        if _matches_adapter(adapter, AdapterType.LABVIEW):
            m_type = AdapterType.LABVIEW.value
            try:
                m_po = module.as_property_object()
                if m_po.Exists("ViCall", 0):
                    vicall = m_po.GetPropertyObject("ViCall", 0)
                    if vicall.Exists("VIPath", 0):
                        vi_path = vicall.GetValString("VIPath", 0).strip()
                        if vi_path:
                            path = vi_path
                            extra["vi_path"] = vi_path
                    if vicall.Exists("ProjectPath", 0):
                        proj_path = vicall.GetValString("ProjectPath", 0).strip()
                        if proj_path:
                            if not path:
                                path = proj_path
                            extra["project_path"] = proj_path
                    if vicall.Exists("ClassPath", 0):
                        cls_path = vicall.GetValString("ClassPath", 0).strip()
                        if cls_path:
                            if not path:
                                path = cls_path
                            extra["class_path"] = cls_path
                    if vicall.Exists("RemoteVIPath", 0):
                        rem_vi = vicall.GetValString("RemoteVIPath", 0).strip()
                        if rem_vi:
                            extra["remote_vi_path"] = rem_vi
                    if vicall.Exists("RemoteProjectPath", 0):
                        rem_proj = vicall.GetValString("RemoteProjectPath", 0).strip()
                        if rem_proj:
                            extra["remote_project_path"] = rem_proj
            except Exception as e:
                logger.debug(f"Could not read LabVIEW module properties: {e}")

            if not path:
                try:
                    lv = module.as_labview_module()
                    path = lv.vi_path or lv.project_path or lv.class_path
                    if lv.vi_path:
                        extra["vi_path"] = lv.vi_path
                    if lv.project_path:
                        extra["project_path"] = lv.project_path
                    if lv.class_path:
                        extra["class_path"] = lv.class_path
                    try:
                        remote_vi = lv.remote_vi_path
                        if remote_vi:
                            extra["remote_vi_path"] = remote_vi
                    except Exception:
                        pass
                    try:
                        remote_proj = lv.remote_project_path
                        if remote_proj:
                            extra["remote_project_path"] = remote_proj
                    except Exception:
                        pass
                except Exception:
                    pass

        elif _matches_adapter(adapter, AdapterType.CVI) or "DLL" in adapter:
            try:
                module_property_object = module.as_property_object()
                for prop in [
                    PropertyPath.MODULE_PATH,
                    PropertyPath.DLL_PATH,
                    PropertyPath.PROJECT_FILE_PATH,
                    PropertyPath.SOURCE_FILE_PATH,
                ]:
                    if module_property_object.exists(prop):
                        path = module_property_object.get_val_string(prop, 0)
                        if path:
                            break
            except Exception as e:
                logger.debug(f"Could not read CVI/DLL module path: {e}")
                path = ""

            m_type = (
                AdapterType.CVI.value
                if _matches_adapter(adapter, AdapterType.CVI)
                else AdapterType.DLL.value
            )

        elif _matches_adapter(adapter, AdapterType.DOTNET):
            dn = module.as_dot_net_module()
            path = dn.assembly_name
            m_type = AdapterType.DOTNET.value
            try:
                if dn.assembly_name:
                    extra["assembly_name"] = dn.assembly_name
                if dn.class_name:
                    extra["class_name"] = dn.class_name
                if dn.member_name:
                    extra["member_name"] = dn.member_name
            except Exception as e:
                logger.debug(f"Could not extract .NET module details: {e}")

        elif _matches_adapter(adapter, AdapterType.PYTHON):
            m_type = AdapterType.PYTHON.value
            try:
                py_mod = module.as_python_module()
                path = py_mod.module_path
                if py_mod.module_path:
                    extra["module_path"] = py_mod.module_path
                if py_mod.class_name:
                    extra["class_name"] = py_mod.class_name
                if py_mod.function_or_attribute_name:
                    extra["function_name"] = py_mod.function_or_attribute_name
            except Exception as e:
                logger.debug(f"Could not extract Python module details via API: {e}")

            if not path:
                try:
                    mpo = module.as_property_object()
                    mod_p = f"PythonCall.{PropertyPath.MODULE_PATH.value}"
                    cls_p = f"PythonCall.{PropertyPath.CLASS_NAME.value}"
                    fn_p = f"PythonCall.{PropertyPath.FUNCTION_OR_ATTRIBUTE_NAME.value}"

                    if mpo.exists(mod_p):
                        path = mpo.get_val_string(mod_p, 0)
                        extra["module_path"] = path
                    if mpo.exists(cls_p):
                        extra["class_name"] = mpo.get_val_string(cls_p, 0)
                    if mpo.exists(fn_p):
                        extra["function_name"] = mpo.get_val_string(fn_p, 0)
                except Exception as e:
                    logger.debug(f"Could not read Python module path via PropertyObject: {e}")

        elif _matches_adapter(adapter, AdapterType.SEQUENCE):
            property_object = step.as_property_object()
            if property_object.get_val_boolean("TS.SData.UseCurFile", 0):
                path = "<Current File>"
            else:
                path = property_object.get_val_string("TS.SData.SFPath", 0)
            m_type = AdapterType.SEQUENCE.value

    except Exception as e:
        logger.debug(f"Could not extract module info for adapter {adapter}: {e}")

    if not path:
        try:
            property_object = step.as_property_object()
            for prop in [
                PropertyPath.CALL_LIB_PATH,
                PropertyPath.CALL_SCRIPT_PATH,
                PropertyPath.CALL_CODE_FILE_PATH,
                PropertyPath.CALL_MODULE_NAME,
                PropertyPath.CALL_PROJECT_PATH,
            ]:
                if property_object.exists(prop):
                    path = property_object.get_val_string(prop, 0)
                    if path:
                        break
        except Exception as e:
            logger.debug(f"Could not read fallback module path: {e}")

    if path:
        result: dict[str, Any] = {"path": path, "type": m_type}
        if extra:
            result["extra"] = extra
        try:
            module_property_object = module.as_property_object()
            # Parameters path varies by adapter
            params_path = ""
            if module_property_object.exists("Parameters"):
                params_path = "Parameters"
            elif module_property_object.exists("Call.Parms"):
                params_path = "Call.Parms"

            if params_path:
                params_property_object = module_property_object.get_property_object(params_path, 0)
                if params_property_object:
                    result["parameters"] = serialize_property_object(params_property_object)
        except Exception as e:
            logger.debug(f"Could not serialize module parameters: {e}")
        return result
    return None


def normalize_adapter(raw_adapter: str | None) -> str:
    """Normalize raw adapter key name to display name."""
    if not raw_adapter:
        return AdapterType.BUILTIN.value

    adapter_lower = raw_adapter.lower()
    for adapter_type, patterns in _ADAPTER_PATTERN_MAP.items():
        if any(p in adapter_lower for p in patterns):
            return adapter_type.value

    return raw_adapter


_ADAPTER_PATTERN_MAP: dict[AdapterType, list[str]] = {
    AdapterType.LABVIEW: ["labview", "g flexible", "g "],
    AdapterType.DOTNET: ["dotnet", ".net"],
    AdapterType.CVI: ["cvi"],
    AdapterType.DLL: ["dll"],
    AdapterType.SEQUENCE: ["sequence"],
    AdapterType.PYTHON: ["python"],
    AdapterType.ACTIVEX: ["activex", "com"],
    AdapterType.BUILTIN: ["none"],
}


def _matches_adapter(adapter: str, adapter_type: AdapterType) -> bool:
    """Check if adapter string matches AdapterType."""
    patterns = _ADAPTER_PATTERN_MAP.get(adapter_type, [])
    adapter_lower = adapter.lower()
    return any(p in adapter_lower for p in patterns)
