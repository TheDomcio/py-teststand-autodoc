"""Station options by category."""

from __future__ import annotations

from typing import Any

from py_teststand import SearchDirectoryType

from .markdown.tables import format_row, format_sep
from .markdown.text import sanitize

# Map SearchDirectoryType enum to human-readable names
SEARCH_DIRECTORY_TYPE_NAMES: dict[int, str] = {
    SearchDirectoryType.TestStandDir: "TestStand Directory",
    SearchDirectoryType.TestStandBinDir: "TestStand Bin Directory",
    SearchDirectoryType.AdapterSupportDir: "Adapter Support Directory",
    SearchDirectoryType.ApplicationDir: "Application Directory",
    SearchDirectoryType.InitialWorkingDir: "Initial Working Directory",
    SearchDirectoryType.WindowsSystemDir: "Windows System Directory",
    SearchDirectoryType.WindowsDir: "Windows Directory",
    SearchDirectoryType.PathEnvironmentVarDir: "Path Environment Variable",
    SearchDirectoryType.CurrentSequenceFileDir: "Current Sequence File Directory",
    SearchDirectoryType.PublicComponentsDir: "Public Components Directory",
    SearchDirectoryType.NIComponentsDir: "NI Components Directory",
    SearchDirectoryType.CurrentWorkspaceDir: "Current Workspace Directory",
    SearchDirectoryType.ContainingProjectDir: "Containing Project Directory",
    SearchDirectoryType.ExplicitDir: "Explicit Directory",
    SearchDirectoryType.TestStandPublicDir: "TestStand Public Directory",
}

STATION_OPTION_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "General": [
        ("station_id", "Station ID"),
        ("language", "Language"),
        ("use_localized_decimal_point", "Use Localized Decimal Point"),
        ("login_on_start", "Login On Start"),
        ("auto_login_system_user", "Auto Login System User"),
        ("require_user_login", "Require User Login"),
    ],
    "Execution": [
        ("rte_option", "RTE Option"),
        ("always_goto_cleanup_on_failure", "Always Goto Cleanup On Failure"),
        ("interactive_branch_mode", "Interactive Branch Mode"),
        ("interactive_exe_propagate_status", "Interactive Exe Propagate Status"),
        ("break_on_step_failure", "Break On Step Failure"),
        ("break_on_sequence_failure", "Break On Sequence Failure"),
        ("breakpoints_enabled", "Breakpoints Enabled"),
        ("tracing_enabled", "Tracing Enabled"),
        ("disable_results", "Disable Results"),
    ],
    "Debug": [
        ("debug_options", "Debug Options"),
        ("show_hidden_properties", "Show Hidden Properties"),
    ],
    "Models and Sequences": [
        ("use_station_model", "Use Station Model"),
        ("allow_other_models", "Allow Other Models"),
        ("station_model_sequence_file_path", "Station Model Sequence File Path"),
    ],
    "File and Source Control": [
        ("check_out_files_when_edited", "Check Out Files When Edited"),
        ("check_out_only_selected_files", "Check Out Only Selected Files"),
        ("use_dialog_for_check_out", "Use Dialog For Check Out"),
        ("prompt_when_adding_files_to_sc", "Prompt When Adding Files To SC"),
        ("file_modification_indicator_policy", "File Modification Indicator Policy"),
        ("default_file_writing_format", "Default File Writing Format"),
        ("system_default_source_code_control", "System Default Source Code Control"),
    ],
    "Variables": [
        ("auto_create_variable_location", "Auto Create Variable Location"),
    ],
    "UI and Messages": [
        ("ui_message_delay", "UI Message Delay"),
        ("ui_message_min_delay", "UI Message Min Delay"),
        ("show_engine_tray_icon_on_remote_stations", "Show Engine Tray Icon On Remote Stations"),
        ("prompt_to_find_files", "Prompt To Find Files"),
        ("recognize_mb_chars", "Recognize MB Chars"),
    ],
    "Remote Access": [
        ("allow_sequence_calls_from_remote_machine", "Allow Sequence Calls From Remote Machine"),
        (
            "allow_all_users_access_from_remote_machine",
            "Allow All Users Access From Remote Machine",
        ),
    ],
    "Preload and Performance": [
        ("preload_progress_delay", "Preload Progress Delay"),
        ("allow_cancelling_preload_expression", "Allow Cancelling Preload Expression"),
        ("reload_workspace_at_startup", "Reload Workspace At Startup"),
        ("reload_docs_when_opening_workspace", "Reload Docs When Opening Workspace"),
    ],
    "Type System": [
        ("allow_automatic_type_conflict_resolution", "Allow Automatic Type Conflict Resolution"),
        ("type_version_auto_increment_option", "Type Version Auto Increment Option"),
        ("type_version_auto_increment_prompt", "Type Version Auto Increment Prompt"),
        ("specify_steps_by_unique_id_in_expressions", "Specify Steps By Unique ID In Expressions"),
    ],
    "Execution Mask": [
        ("execution_mask", "Execution Mask"),
    ],
    "CPU Affinity": [
        ("default_cpu_affinity_for_threads", "Default CPU Affinity For Threads"),
        ("default_cpu_affinity_for_threads_ex", "Default CPU Affinity For Threads Ex"),
    ],
    "Sequence File Versioning": [
        ("seq_file_version_auto_increment_option", "Sequence File Version Auto Increment Option"),
    ],
    "User File": [
        ("user_file_path", "User File Path"),
    ],
}


def _format_value(value: Any) -> str:
    if value is None:
        return "(not available)"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def append_search_directories(md: list[str], engine: Any) -> None:
    md.append("### Search Directories")
    md.append("")
    md.append(format_row(["Type", "Path", "Search Subdirectories", "Disabled"]))
    md.append(format_sep(4))
    try:
        search_dirs = engine.search_directories
        for search_dir in search_dirs:
            dir_type = SEARCH_DIRECTORY_TYPE_NAMES.get(
                search_dir.type,
                f"Unknown ({search_dir.type})",
            )
            path = search_dir.path or "(empty)"
            subdirs = "Yes" if search_dir.search_subdirectories else "No"
            disabled = "Yes" if search_dir.disabled else "No"
            md.append(format_row([sanitize(dir_type), sanitize(path), subdirs, disabled]))
    except Exception as error:
        md.append(format_row([f"Error: {sanitize(str(error))}", "", "", ""]))
    md.append("")


def append_station_globals(md: list[str], engine: Any) -> None:
    md.append("### Station Globals")
    md.append("")
    try:
        with engine.globals as station_globals:
            from ..shared.property_serializer import serialize_property_object

            globals_list = serialize_property_object(station_globals)
            if globals_list:
                md.append(format_row(["Name", "Type"]))
                md.append(format_sep(2))
                for var in globals_list:
                    name = sanitize(var.get("name", ""))
                    type_name = sanitize(var.get("type", ""))
                    md.append(format_row([name, type_name]))
            else:
                md.append("(no station globals)")
    except Exception as error:
        md.append(f"(error reading station globals: {sanitize(str(error))})")
    md.append("")


def append_station_options(md: list[str], engine: Any) -> None:
    md.append("---")
    md.append("")
    md.append("## Station Options")
    md.append("")

    try:
        with engine.station_options as station_options:
            for category, properties in STATION_OPTION_CATEGORIES.items():
                try:
                    has_properties = any(
                        hasattr(station_options, prop_name) for prop_name, _ in properties
                    )
                    if not has_properties:
                        continue

                    md.append(f"### {category}")
                    md.append("")
                    md.append(format_row(["Option", "Value"]))
                    md.append(format_sep(2))

                    for prop_name, display_name in properties:
                        try:
                            value = getattr(station_options, prop_name, None)
                            if value is not None:
                                md.append(
                                    format_row(
                                        [sanitize(display_name), sanitize(_format_value(value))],
                                    ),
                                )
                        except Exception as error:
                            md.append(
                                format_row([sanitize(display_name), f"({sanitize(str(error))})"]),
                            )

                    md.append("")
                except Exception as error:
                    md.append(f"**Error reading {category}**: {sanitize(str(error))}")
                    md.append("")
    except Exception as error:
        md.append(f"**Error reading station options**: {sanitize(str(error))}")
        md.append("")

    append_station_globals(md, engine)
    append_search_directories(md, engine)
