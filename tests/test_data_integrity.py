from py_teststand_autodoc import Extractor


class TestDataIntegrity:
    def test_no_missing_sequences(self, engine, seq_file):
        ext = Extractor(engine)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        for seq_name in ["MainSequence", "Subsequence_A", "Subsequence_B", "ProcessSetup"]:
            assert seq_name in md

    def test_no_missing_steps(self, engine, seq_file):
        ext = Extractor(engine)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        expected_steps = [
            "Setup_Step_1",
            "Setup_Step_2",
            "Call_Subsequence_A",
            "Call_Subsequence_B",
            "Main_Step_3",
            "Sub_A_Step_1",
            "Sub_A_Step_2",
            "Looping_Step",
        ]
        for step_name in expected_steps:
            assert step_name in md

    def test_limit_formatting_consistency(self, engine, seq_file):
        ext = Extractor(engine, include_station_options=False)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "5" in md
        assert "5.0" not in md

    def test_variable_scopes_isolation(self, engine, seq_file):
        ext = Extractor(engine, include_scopes=["Locals"])
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "#### Locals" in md
        assert "#### Parameters" not in md

        ext = Extractor(engine, include_scopes=["Parameters"])
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "#### Parameters" in md
        assert "#### Locals" not in md

    def test_module_path_serialization(self, engine, seq_file):
        ext = Extractor(engine)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "N/A" not in md

    def test_mermaid_diagram_integrity(self, engine, seq_file):
        ext = Extractor(engine, include_flowcharts=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "flowchart TD" in md
        assert "-->" in md
        assert "subgraph" not in md
