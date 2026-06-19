from py_teststand_autodoc import Extractor


class TestExtractorApi:
    def test_full_pipeline(self, engine, seq_file):
        ext = Extractor(engine)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert len(md) > 500
        assert "MainSequence" in md
        assert "Subsequence_A" in md
        assert "Subsequence_B" in md

    def test_with_process_models(self, engine, seq_file):
        ext = Extractor(engine, include_process_models=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "MainSequence" in md

    def test_with_scopes(self, engine, seq_file):
        ext = Extractor(engine, include_scopes=["Locals", "Parameters"])
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "Local_Var_1" in md
        assert "Counter" in md
        assert "Param_A" in md
        assert "Sub_Local_1" in md
        assert "Sub_Param_1" in md

    def test_with_extended_syntax(self, engine, seq_file):
        ext = Extractor(engine, extended_syntax=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "```mermaid" in md
        assert '!!! info "Description"' in md

    def test_with_station_options(self, engine, seq_file):
        ext = Extractor(engine, include_station_options=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "## Station Options" in md

    def test_with_types(self, engine, seq_file):
        ext = Extractor(engine, include_types=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "## Custom Types" in md

    def test_ignore_skipped(self, engine, seq_file):
        ext = Extractor(engine, ignore_skipped=True)
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "Deprecated_Step" not in md

    def test_business_profile(self, engine, seq_file):
        ext = Extractor(engine, profile="business")
        ext.analyze_hierarchy(str(seq_file))
        md = ext.to_markdown()

        assert "- **Setup_Step_1**" in md
        assert "|Technology|" not in md
