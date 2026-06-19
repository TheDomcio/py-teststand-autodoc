from pathlib import Path

import pytest
from py_teststand import Engine, PropertyOption, PropValType, RunMode, SequenceType, StepGroup

# Monkeypatch Engine.release to be a no-op during tests to prevent deadlocks/hangs
# on session teardown. We exit the process using os._exit anyway, so cleanup is handled by OS.
Engine.release = lambda _: None  # type: ignore


SEQ_FILE_PATH = Path(__file__).parent.parent / "tmp" / "test_output.seq"


@pytest.fixture(scope="session", autouse=True)
def cleanup_seq_file():
    yield
    if SEQ_FILE_PATH.exists():
        SEQ_FILE_PATH.unlink()


def create_test_sequence_file(engine: Engine, path: Path) -> None:
    seq_file = engine.new_sequence_file()

    # === MainSequence (Entry Point) ===
    main_seq = seq_file.get_sequence_by_name("MainSequence")
    main_seq.type = SequenceType.ExeEntryPoint
    main_seq.entry_point_menu_hint = "Run Main"
    main_seq.comment = "Description"

    # Add locals
    main_seq.locals.new_sub_property(
        "Local_Var_1",
        PropValType.Number,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    main_seq.locals.set_val_number("Local_Var_1", 0, 0.0)
    main_seq.locals.new_sub_property(
        "Local_Var_2",
        PropValType.String,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    main_seq.locals.set_val_string("Local_Var_2", 0, "Placeholder")
    main_seq.locals.new_sub_property(
        "Counter",
        PropValType.Number,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    main_seq.locals.set_val_number("Counter", 0, 0)

    # Add parameters
    main_seq.parameters.new_sub_property(
        "Param_A",
        PropValType.String,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    main_seq.parameters.set_val_string("Param_A", 0, "Default")

    # Generic initialization Action step
    setup_step_1 = main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Setup_Step_1",
        index=0,
        group=StepGroup.Setup,
    )
    setup_step_1.as_property_object().Comment = "Initialize resources"

    # Generic configuration Action step
    config_step = main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Setup_Step_2",
        index=1,
        group=StepGroup.Setup,
    )
    config_step.run_mode = RunMode.Normal

    # Main steps - sequence calls
    main_seq.new_step(
        adapter_name="Sequence Adapter",
        step_type_name="SequenceCall",
        name="Call_Subsequence_A",
        index=0,
        group=StepGroup.Main,
    )

    main_seq.new_step(
        adapter_name="Sequence Adapter",
        step_type_name="SequenceCall",
        name="Call_Subsequence_B",
        index=1,
        group=StepGroup.Main,
    )

    # Action step with precondition and routing
    verify_step = main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Main_Step_3",
        index=2,
        group=StepGroup.Main,
    )
    verify_step.precondition = "Locals.Local_Var_1 > 0"
    verify_step.custom_action_expression = "Locals.Counter = Locals.Counter + 1"

    # Skipped step
    skip_step = main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Deprecated_Step",
        index=3,
        group=StepGroup.Main,
    )
    skip_step.run_mode = RunMode.Skip

    # Loop step
    loop_step = main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Looping_Step",
        index=4,
        group=StepGroup.Main,
    )
    loop_step.as_property_object().set_val_string("TS.LoopWhileExpr", 1, "Locals.Counter < 5")
    loop_step.as_property_object().set_val_string("TS.LoopIncrementExpr", 1, "Locals.Counter += 1")

    # Cleanup
    main_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Cleanup_Step",
        index=0,
        group=StepGroup.Cleanup,
    )

    # === Subsequence_A ===
    sub_seq_a = seq_file.new_sequence("Subsequence_A")
    sub_seq_a.type = SequenceType.Normal

    sub_seq_a.locals.new_sub_property(
        "Sub_Local_1",
        PropValType.Number,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    sub_seq_a.locals.set_val_number("Sub_Local_1", 0, 5.0)

    step_a1 = sub_seq_a.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Sub_A_Step_1",
        index=0,
        group=StepGroup.Main,
    )
    step_a1.custom_action_expression = "Locals.Sub_Local_1 = -46.0"

    step_a2 = sub_seq_a.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Sub_A_Step_2",
        index=1,
        group=StepGroup.Main,
    )
    step_a2.precondition = "Locals.Sub_Local_1 != 0"

    # === Subsequence_B ===
    sub_seq_b = seq_file.new_sequence("Subsequence_B")
    sub_seq_b.type = SequenceType.Normal

    sub_seq_b.parameters.new_sub_property(
        "Sub_Param_1",
        PropValType.Number,
        False,
        "",
        PropertyOption.InsertIfMissing,
    )
    sub_seq_b.parameters.set_val_number("Sub_Param_1", 0, 1000.0)

    step_b1 = sub_seq_b.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Sub_B_Step_1",
        index=0,
        group=StepGroup.Main,
    )
    step_b1.custom_action_expression = "Parameters.Sub_Param_1 = 1000"

    sub_seq_b.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Sub_B_Step_2",
        index=1,
        group=StepGroup.Main,
    )

    # === SequenceFileLoad (Callback) ===
    load_seq = seq_file.new_sequence("SequenceFileLoad")
    load_seq.type = SequenceType.Callback

    log_step = load_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Callback_Step_1",
        index=0,
        group=StepGroup.Main,
    )
    log_step.custom_action_expression = 'RunState.TestSocket.Message = "Loaded"'

    # === ProcessSetup (Callback) ===
    setup_cb = seq_file.new_sequence("ProcessSetup")
    setup_cb.type = SequenceType.Callback

    setup_cb.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Callback_Step_2",
        index=0,
        group=StepGroup.Main,
    )

    # === PostMainSequence (Callback) ===
    post_seq = seq_file.new_sequence("PostMainSequence")
    post_seq.type = SequenceType.Callback

    post_seq.new_step(
        adapter_name="None Adapter",
        step_type_name="Action",
        name="Callback_Step_3",
        index=0,
        group=StepGroup.Main,
    )

    seq_file.save(str(path))
    engine.release_sequence_file(seq_file)


_KEEP_ALIVE = []


@pytest.fixture(scope="session")
def engine():
    eng = Engine()
    _KEEP_ALIVE.append(eng)
    yield eng


@pytest.fixture(scope="session")
def seq_file(engine):
    create_test_sequence_file(engine, SEQ_FILE_PATH)
    return SEQ_FILE_PATH


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Exit process immediately to avoid TestStand Engine COM teardown hangs."""
    import os
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitstatus)
