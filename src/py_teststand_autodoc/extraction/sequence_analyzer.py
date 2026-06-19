"""Sequence analysis helpers for data extraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import py_teststand
from py_teststand import SequenceType

from ..constants import CALLBACK_NAMES, PropertyPath
from ..shared.property_serializer import serialize_property_object

if TYPE_CHECKING:
    from py_teststand import Sequence

logger = logging.getLogger(__name__)


def get_sequence_comment(sequence: Sequence) -> str:
    """Safely get sequence comment."""
    try:
        return sequence.comment
    except Exception:
        pass
    return ""


def categorize_sequence(name: str, seq_type: SequenceType) -> str:
    """Categorize sequence based on name and type."""
    entry_types = {SequenceType.ExeEntryPoint, SequenceType.CfgEntryPoint}
    if name == "MainSequence" or seq_type in entry_types:
        return "Entry Point"
    if name in CALLBACK_NAMES or seq_type == SequenceType.Callback:
        if hasattr(py_teststand, "DefaultModelCallback") and any(
            name == e.name for e in py_teststand.DefaultModelCallback
        ):
            return "Model Callback"

        engine_callbacks = {
            "SequenceFilePreStep",
            "SequenceFilePostStep",
            "SequenceFilePreInteractive",
            "SequenceFilePostInteractive",
            "SequenceFileLoad",
            "SequenceFileUnload",
            "SequenceFilePostResultListEntry",
            "SequenceFilePostResults",
            "SequenceFilePostStepRuntimeError",
            "SequenceFilePostStepFailure",
            "ProcessModelPreStep",
            "ProcessModelPostStep",
            "ProcessModelPreInteractive",
            "ProcessModelPostInteractive",
            "ProcessModelPostResultListEntry",
            "ProcessModelPostResults",
            "ProcessModelPostStepRuntimeError",
            "ProcessModelPostStepFailure",
            "StationPreStep",
            "StationPostStep",
            "StationPreInteractive",
            "StationPostInteractive",
            "StationPostResultListEntry",
            "StationPostResults",
            "StationPostStepRuntimeError",
            "StationPostStepFailure",
        }
        if name in engine_callbacks:
            return "Engine Callback"

        front_end_callbacks = {"LoginLogout"}
        if name in front_end_callbacks:
            return "Front-End Callback"

        return "Callback"
    return "Subsequence"


def extract_file_globals(sequence_file: Any) -> list[dict[str, str]]:
    """Extract FileGlobals as flat list of {name, type}."""
    try:
        sequence_file_property_object = sequence_file.as_property_object()
        for key in (PropertyPath.FILE_GLOBALS, "FileGlobals", PropertyPath.FILE_GLOBALS_NAME):
            if sequence_file_property_object.exists(key):
                file_globals_property_object = sequence_file_property_object.get_property_object(
                    key,
                    0,
                )
                return serialize_property_object(file_globals_property_object)
    except Exception as e:
        logger.debug(f"Could not extract file globals: {e}")
    return []


def extract_station_globals(engine: Any) -> list[dict[str, str]]:
    """Extract StationGlobals as flat list of {name, type}."""
    try:
        with engine.globals as station_globals:
            return serialize_property_object(station_globals)
    except Exception as e:
        logger.debug(f"Could not extract station globals: {e}")
    return []


def extract_variables(
    sequence: Sequence,
    data: dict[str, Any],
    include_scopes: list[str],
) -> None:
    """Extract variables from specified scopes."""
    for scope in include_scopes:
        if not scope:
            continue
        scope_lower = scope.lower()
        if scope_lower == "locals":
            data["variables"]["Locals"] = serialize_property_object(sequence.locals)
        elif scope_lower == "parameters":
            data["variables"]["Parameters"] = serialize_property_object(sequence.parameters)
        elif scope_lower == "fileglobals":
            data["variables"]["FileGlobals"] = data.get("file_globals", [])
