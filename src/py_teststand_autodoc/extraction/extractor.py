"""Extractor implementation for sequence data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from py_teststand import (
    ConflictHandler,
    FindFilePromptOption,
    FindFileSearchListOption,
    GetSeqFileOption,
    PropertyOption,
    RunMode,
    StepGroup,
)

from ..constants import PropertyPath
from ..shared.property_serializer import serialize_property_object
from .module_info import get_module_info
from .process_model import is_process_model
from .sequence_analyzer import (
    categorize_sequence,
    extract_file_globals,
    extract_station_globals,
    extract_variables,
    get_sequence_comment,
)
from .step_extraction import build_step_data, expand_multiple_numeric_step, get_call_property

if TYPE_CHECKING:
    from py_teststand import Engine, Sequence, Step

logger = logging.getLogger(__name__)


class HierarchyExtractor:
    """COM parser for sequence hierarchies into Python dicts."""

    def __init__(
        self,
        engine: Engine,
        include_process_models: bool = False,
        include_scopes: list[str] | None = None,
        ignore_skipped: bool = False,
        estimate_software_delays: bool = False,
        include_file_custom_data_types: bool = False,
    ):
        self.engine = engine
        self.include_process_models = include_process_models
        self.include_scopes = include_scopes or []
        self.ignore_skipped = ignore_skipped
        self.estimate_software_delays = estimate_software_delays
        self.include_file_custom_data_types = include_file_custom_data_types

        self._visited_files: set[str] = set()
        self._hierarchy_data: list[dict[str, Any]] = []
        self._modules_used: dict[str, list[dict[str, str | int]]] = {}
        self._station_globals: list[dict[str, str]] = extract_station_globals(engine)

    @property
    def hierarchy_data(self) -> list[dict[str, Any]]:
        return self._hierarchy_data

    @property
    def modules_used(self) -> dict[str, list[dict[str, str | int]]]:
        return self._modules_used

    @property
    def station_globals(self) -> list[dict[str, str]]:
        return self._station_globals

    def extract(self, file_path: str, depth: int = 0) -> None:
        """Recursively extract data from sequence file and child calls."""
        abs_path = str(Path(file_path).absolute())
        if abs_path in self._visited_files:
            return

        if (
            depth > 0
            and not self.include_process_models
            and is_process_model(self.engine, abs_path)
        ):
            return

        logger.info(f"{'  ' * depth}Analyzing: {Path(abs_path).name}")
        self._visited_files.add(abs_path)

        try:
            options = GetSeqFileOption.FindFile | GetSeqFileOption.DoNotRunLoadCallback
            sequence_file = self.engine.get_sequence_file_ex(
                abs_path,
                options,
                ConflictHandler.Error,
            )
            file_data: dict[str, Any] = {
                "name": Path(sequence_file.path).name,
                "path": str(sequence_file.path),
                "sequences": [],
                "depth": depth,
                "file_globals": extract_file_globals(sequence_file),
                "file_version": self._extract_file_version(sequence_file),
                "custom_data_types": self._extract_custom_data_types(sequence_file)
                if self.include_file_custom_data_types
                else [],
            }

            for sequence in sequence_file.get_sequences():
                seq_data = self._analyze_sequence(sequence, abs_path)
                file_data["sequences"].append(seq_data)

                for group in [StepGroup.Setup, StepGroup.Main, StepGroup.Cleanup]:
                    for i in range(sequence.get_num_steps(group)):
                        step = sequence.get_step(i, group)
                        if step.step_type_name == "SequenceCall":
                            self._extract_child_call(step, depth)

            if self.estimate_software_delays:
                file_delay = sum(
                    s.get("estimated_software_delay", 0.0) for s in file_data["sequences"]
                )
                if file_delay > 0:
                    file_data["estimated_software_delay"] = file_delay

            self._hierarchy_data.append(file_data)
            self.engine.release_sequence_file(sequence_file)
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            raise

    def _extract_child_call(self, step: Step, depth: int) -> None:
        """Extract and recurse into child sequence call."""
        try:
            step_property_object = step.as_property_object()
            if step_property_object.get_val_boolean(PropertyPath.USE_CUR_FILE, 0):
                return
            path_expr = get_call_property(
                step_property_object,
                PropertyPath.SEQ_FILE_PATH,
                PropertyPath.SEQ_FILE_PATH_EXPR,
            )
            if not path_expr:
                # An empty path with UseCurFile false still means the current
                # file; there is no child file to follow.
                return
            child_path = self._resolve_child_path(path_expr)
            if child_path:
                self.extract(child_path, depth + 1)
            else:
                logger.warning(f"{'  ' * depth} Missing child file: {path_expr}")
        except Exception as e:
            logger.warning(f"{'  ' * depth}Failed to extract child call: {e}")

    def _resolve_child_path(self, path_expr: str) -> str | None:
        """Resolve a child sequence file path expression to an absolute path."""
        try:
            found, abs_path, _cancelled = self.engine.find_file(
                path_expr,
                prompt_option=FindFilePromptOption.Disable,
                search_list_option=FindFileSearchListOption.Always,
            )
            if found and abs_path:
                return abs_path
        except Exception as e:
            logger.debug(f"find_file failed for {path_expr!r}: {e}")
        return None

    def _extract_file_version(self, sequence_file: Any) -> str:
        """Extract version string from sequence file."""
        try:
            po_file = sequence_file.as_property_object_file()
            return po_file.version or ""
        except Exception as e:
            logger.debug(f"Could not read file version: {e}")
            return ""

    def _extract_custom_data_types(self, sequence_file: Any) -> list[dict[str, Any]]:
        types_list = []
        try:
            po_file = sequence_file.as_property_object_file()
            tul = po_file.type_usage_list
            for i in range(tul.num_types):
                try:
                    if not tul.get_is_type_attached_to_file(i):
                        continue
                    type_def = tul.get_type_definition(i)

                    try:
                        if type_def.attributes.exists("TestStand.StepType", 0):
                            continue
                    except Exception as e:
                        logger.debug(f"Could not check StepType attribute for {type_def.name}: {e}")

                    type_name = type_def.name
                    type_data: dict[str, Any] = {
                        "name": type_name,
                        "type": type_def.get_type_display_string(""),
                        "fields": [],
                        "enumerators": [],
                    }

                    try:
                        for j in range(type_def.get_num_sub_properties("")):
                            sub_name = type_def.get_nth_sub_property_name("", j)
                            v_type = type_def.get_type_display_string(sub_name)
                            type_data["fields"].append({"name": sub_name, "type": v_type})
                    except Exception as e:
                        logger.debug(f"Could not extract fields for type {type_name}: {e}")

                    try:
                        if type_def.enumerators is not None:
                            enum_po = type_def.enumerators
                            for k in range(enum_po.get_num_elements()):
                                elem = enum_po.get_property_object_by_offset(k, 0)
                                if elem is not None:
                                    val = int(
                                        elem.get_val_number("", int(PropertyOption.CoerceToNumber)),
                                    )
                                    enum_name = elem.get_value_display_name("", 0)
                                    type_data["enumerators"].append(
                                        {"name": enum_name, "value": val},
                                    )
                    except Exception as e:
                        logger.debug(f"Could not extract enumerators for type {type_name}: {e}")

                    types_list.append(type_data)
                except Exception as e:
                    logger.debug(f"Could not extract type definition at index {i}: {e}")
        except Exception as e:
            logger.debug(f"Could not extract custom data types: {e}")
        return sorted(types_list, key=lambda t: t["name"])

    def _analyze_sequence(self, sequence: Sequence, file_path: str) -> dict[str, Any]:
        """Analyze a single sequence and extract its steps and variables."""
        seq_type = sequence.type

        category = categorize_sequence(sequence.name, seq_type)

        data: dict[str, Any] = {
            "name": sequence.name,
            "category": category,
            "comment": get_sequence_comment(sequence),
            "variables": {},
            "step_groups": {},
        }

        # Always extract locals/parameters so the engineer profile can show them
        # inline; extract_variables also honours include_scopes for other callers.
        try:
            locals_list = serialize_property_object(sequence.locals)
            if locals_list:
                data["variables"]["Locals"] = locals_list
        except Exception as e:
            logger.debug(f"Could not serialize locals for {sequence.name}: {e}")
        try:
            params_list = serialize_property_object(sequence.parameters)
            if params_list:
                data["variables"]["Parameters"] = params_list
        except Exception as e:
            logger.debug(f"Could not serialize parameters for {sequence.name}: {e}")

        extract_variables(sequence, data, self.include_scopes)

        if "Locals" not in self.include_scopes:
            data["variables"].pop("Locals", None)
        if "Parameters" not in self.include_scopes:
            data["variables"].pop("Parameters", None)
        if "FileGlobals" not in self.include_scopes:
            data["variables"].pop("FileGlobals", None)

        self._extract_steps(sequence, file_path, data)

        if self.estimate_software_delays:
            total_delay = 0.0
            for group_steps in data["step_groups"].values():
                for step in group_steps:
                    total_delay += step.get("estimated_delay", 0.0)
            if total_delay > 0:
                data["estimated_software_delay"] = total_delay

        return data

    def _extract_steps(self, sequence: Sequence, file_path: str, data: dict[str, Any]) -> None:
        """Extract steps from all step groups."""
        for group in [StepGroup.Setup, StepGroup.Main, StepGroup.Cleanup]:
            steps = []
            for i in range(sequence.get_num_steps(group)):
                step = sequence.get_step(i, group)
                step_property_object = step.as_property_object()

                skipped = step.run_mode == RunMode.Skip
                if self.ignore_skipped and skipped:
                    continue

                module_info = get_module_info(step)
                if module_info:
                    if file_path not in self._modules_used:
                        self._modules_used[file_path] = []

                    found = False
                    for m in self._modules_used[file_path]:
                        # Compare path and type to aggregate occurrences
                        if m.get("path") == module_info.get("path") and m.get(
                            "type"
                        ) == module_info.get("type"):
                            m["occurrences"] = int(m.get("occurrences", 1)) + 1
                            found = True
                            break
                    if not found:
                        m_copy = dict(module_info)
                        m_copy["occurrences"] = 1
                        self._modules_used[file_path].append(m_copy)

                if step.step_type_name == "NI_MultipleNumericLimitTest":
                    expanded = expand_multiple_numeric_step(
                        step,
                        step_property_object,
                        module_info,
                        skipped=skipped,
                    )
                    steps.extend(expanded)
                else:
                    step_data = build_step_data(
                        step,
                        step_property_object,
                        module_info,
                        skipped=skipped,
                    )
                    steps.append(step_data)

            data["step_groups"][group.name] = steps
