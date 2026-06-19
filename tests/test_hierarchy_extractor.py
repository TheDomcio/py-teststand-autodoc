from pathlib import Path

from py_teststand_autodoc.extraction.extractor import HierarchyExtractor


class TestHierarchyExtractor:
    def test_extract_hierarchy(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        assert len(ext.hierarchy_data) == 1
        file_data = ext.hierarchy_data[0]
        assert Path(file_data["path"]).name == Path(seq_file).name

        seq_names = {s["name"] for s in file_data["sequences"]}
        expected = {
            "MainSequence",
            "Subsequence_A",
            "Subsequence_B",
            "SequenceFileLoad",
            "ProcessSetup",
            "PostMainSequence",
        }
        assert expected.issubset(seq_names)

    def test_extract_entry_point_category(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        assert main_seq["category"] == "Entry Point"

    def test_extract_callback_category(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        seq = next(s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "SequenceFileLoad")
        assert seq["category"] == "Engine Callback"

        for cb_name in ["ProcessSetup", "PostMainSequence"]:
            seq = next(s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == cb_name)
            assert seq["category"] == "Model Callback"

    def test_extract_subsequence_category(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        for sub_name in ["Subsequence_A", "Subsequence_B"]:
            seq = next(s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == sub_name)
            assert seq["category"] == "Subsequence"

    def test_extract_step_groups(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        assert "Setup" in main_seq["step_groups"]
        assert "Main" in main_seq["step_groups"]
        assert "Cleanup" in main_seq["step_groups"]

    def test_extract_setup_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        setup_steps = main_seq["step_groups"]["Setup"]
        assert len(setup_steps) == 2

        step_names = [s["name"] for s in setup_steps]
        assert "Setup_Step_1" in step_names
        assert "Setup_Step_2" in step_names

    def test_extract_main_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        main_steps = main_seq["step_groups"]["Main"]
        assert len(main_steps) == 5

        step_names = [s["name"] for s in main_steps]
        assert "Call_Subsequence_A" in step_names
        assert "Call_Subsequence_B" in step_names
        assert "Main_Step_3" in step_names
        assert "Deprecated_Step" in step_names
        assert "Looping_Step" in step_names

    def test_extract_sequence_call_target(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        rf_call = next(
            s for s in main_seq["step_groups"]["Main"] if s["name"] == "Call_Subsequence_A"
        )
        assert rf_call["type"] == "SequenceCall"
        assert "target_sequence" in rf_call

    def test_extract_precondition(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        verify = next(s for s in main_seq["step_groups"]["Main"] if s["name"] == "Main_Step_3")
        assert verify["precondition"] == "Locals.Local_Var_1 > 0"

    def test_extract_skipped_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        main_steps = main_seq["step_groups"]["Main"]
        step_names = [s["name"] for s in main_steps]
        assert "Deprecated_Step" in step_names

    def test_ignore_skipped_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine, ignore_skipped=True)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        main_steps = main_seq["step_groups"]["Main"]
        step_names = [s["name"] for s in main_steps]
        assert "Deprecated_Step" not in step_names
        assert len(main_steps) == 4

    def test_extract_sequence_comment(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        main_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "MainSequence"
        )
        assert "comment" in main_seq

    def test_extract_subsequence_a_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        rf_seq = next(s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "Subsequence_A")
        main_steps = rf_seq["step_groups"]["Main"]
        assert len(main_steps) == 2

        step_names = [s["name"] for s in main_steps]
        assert "Sub_A_Step_1" in step_names
        assert "Sub_A_Step_2" in step_names

    def test_extract_subsequence_b_steps(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        audio_seq = next(
            s for s in ext.hierarchy_data[0]["sequences"] if s["name"] == "Subsequence_B"
        )
        main_steps = audio_seq["step_groups"]["Main"]
        assert len(main_steps) == 2

        step_names = [s["name"] for s in main_steps]
        assert "Sub_B_Step_1" in step_names
        assert "Sub_B_Step_2" in step_names

    def test_no_duplicate_files(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))
        ext.extract(str(seq_file))

        assert len(ext.hierarchy_data) == 1

    def test_modules_used_empty_for_builtin(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))

        for modules in ext.modules_used.values():
            assert len(modules) == 0
