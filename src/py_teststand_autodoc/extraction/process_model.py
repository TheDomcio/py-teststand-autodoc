"""Helpers for detecting sequencer process model files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from py_teststand import ConflictHandler, GetSeqFileOption, SequenceFileType

from ..constants import PROCESS_MODEL_FILENAMES, PROCESS_MODEL_PATTERNS

if TYPE_CHECKING:
    from py_teststand import Engine


def is_process_model(engine: Engine, path: str | None) -> bool:
    """Determine if path points to sequencer process model."""
    if not path:
        return False

    if _check_file_type(engine, path):
        return True

    return _check_path_patterns(path)


def _check_file_type(engine: Engine, path: str) -> bool:
    """Check file's SequenceFileType via COM."""
    try:
        sequence_file = engine.get_sequence_file_ex(
            path,
            GetSeqFileOption.FindFile,
            ConflictHandler.Error,
        )
        is_model = sequence_file.sequence_file_type == SequenceFileType.Model
        engine.release_sequence_file(sequence_file)
        return is_model
    except Exception:
        return False


def _check_path_patterns(path: str) -> bool:
    """Check if path matches known process model patterns."""
    path_lower = path.lower()

    for pattern in PROCESS_MODEL_PATTERNS:
        if pattern in path_lower:
            return True

    filename = Path(path_lower).name
    return filename in PROCESS_MODEL_FILENAMES
