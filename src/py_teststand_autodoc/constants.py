"""Constants, enums, and mappings for autodoc generator."""

from __future__ import annotations

from enum import StrEnum

from py_teststand import DefaultModelCallback

CALLBACK_NAMES: frozenset[str] = frozenset(
    {cb.value for cb in DefaultModelCallback}
    | {
        "SequenceFileLoad",
        "SequenceFileUnload",
        "ProcessCleanup",
        "ProcessSetup",
        "PreBatch",
        "PostBatch",
        "PreBatchLoop",
        "PostBatchLoop",
        "TestReport",
        "PostStepRuntimeError",
        "GetReportFilePath",
    },
)

PROCESS_MODEL_PATTERNS: list[str] = [
    "components\\models",
    "model.sequence",
    "modelsupport.sequence",
]

PROCESS_MODEL_FILENAMES: frozenset[str] = frozenset(
    {
        "sequentialmodel.sequence",
        "parallelmodel.sequence",
        "batchmodel.sequence",
    },
)


class AdapterType(StrEnum):
    """Normalized adapter display names."""

    BUILTIN = "Built-in"
    LABVIEW = "LabVIEW"
    DOTNET = ".NET"
    CVI = "LabWindows/CVI"
    DLL = "C/C++ DLL"
    SEQUENCE = "Sequence"
    PYTHON = "Python"
    ACTIVEX = "ActiveX/COM"


class PropertyPath(StrEnum):
    LIMITS_LOW = "Limits.Low"
    LIMITS_HIGH = "Limits.High"
    LIMITS_STRING = "Limits.String"
    COMP = "Comp"
    UNITS = "Units"
    RESULT_UNITS = "Result.Units"
    IGNORE_CASE = "IgnoreCase"
    DATA_SOURCE = "DataSource"

    CALL_LIB_PATH = "TS.SData.Call.LibPath"
    CALL_SCRIPT_PATH = "TS.SData.Call.ScriptPath"
    CALL_CODE_FILE_PATH = "TS.SData.Call.CodeFilePath"
    CALL_MODULE_NAME = "TS.SData.Call.ModuleName"
    CALL_PROJECT_PATH = "TS.SData.Call.ProjectPath"

    # SequenceCall target: expression or plain property.
    USE_CUR_FILE = "TS.SData.UseCurFile"
    SEQ_FILE_PATH = "TS.SData.SFPath"
    SEQ_FILE_PATH_EXPR = "TS.SData.SFPathExpr"
    TARGET_SEQUENCE = "TS.SData.SeqName"
    TARGET_SEQUENCE_EXPR = "TS.SData.SeqNameExpr"

    # LabVIEW module SData properties.
    LV_VI_PATH = "TS.SData.ViCall.VIPath"
    LV_PROJECT_PATH = "TS.SData.ViCall.ProjectPath"
    LV_CLASS_PATH = "TS.SData.Class.ClassPath"
    LV_CALL_TYPE = "TS.SData.CallType"
    LV_REMOTE_VI_PATH = "TS.SData.RemoteViPath"
    LV_REMOTE_PROJECT_PATH = "TS.SData.RemoteProjectPath"

    MODULE_PATH = "ModulePath"
    DLL_PATH = "DllPath"
    PROJECT_FILE_PATH = "ProjectFilePath"
    SOURCE_FILE_PATH = "SourceFilePath"
    CLASS_NAME = "ClassName"
    FUNCTION_OR_ATTRIBUTE_NAME = "FunctionOrAttributeName"

    # FileGlobals property paths.
    FILE_GLOBALS = "Data.SeqFileGlobals"
    FILE_GLOBALS_NAME = "SeqFileGlobals"


__all__ = [
    "CALLBACK_NAMES",
    "PROCESS_MODEL_FILENAMES",
    "PROCESS_MODEL_PATTERNS",
    "AdapterType",
    "PropertyPath",
]
