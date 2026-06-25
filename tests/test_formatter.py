import pytest

from py_teststand_autodoc import Extractor
from py_teststand_autodoc.extraction.extractor import HierarchyExtractor
from py_teststand_autodoc.rendering.formatter import Formatter


class TestFormatter:
    @pytest.fixture
    def extracted_data(self, engine, seq_file):
        ext = HierarchyExtractor(engine)
        ext.extract(str(seq_file))
        return ext.hierarchy_data, ext.modules_used

    def test_engineer_profile_output(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "# test_output" in md
        assert "# test_output" in md
        assert "*Entry Point*" in md
        assert "*Subsequence*" in md
        assert "*Engine Callback*" in md
        assert "**Sequences**" in md
        assert "Engine Callback: 1" in md
        assert "Model Callback: 2" in md

    def test_engineer_profile_step_table(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "Setup_Step_1" in md
        assert "Call_Subsequence_A" in md

    def test_business_profile_output(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="business")
        md = fmt.format(hierarchy_data, modules_used)

        assert "Setup_Step_1" in md
        assert "Call_Subsequence_A" in md

    def test_business_profile_no_tech_column(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="business")
        md = fmt.format(hierarchy_data, modules_used)

        assert "|Technology|" not in md

    def test_include_flowcharts_mermaid(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(include_flowcharts=True)
        md = fmt.format(hierarchy_data, modules_used)

        assert "```mermaid" in md
        assert "flowchart TD" in md

    def test_include_flowcharts_admonitions(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(include_flowcharts=True)
        md = fmt.format(hierarchy_data, modules_used)

        assert "```mermaid" in md

    def test_table_of_contents_removed(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter()
        md = fmt.format(hierarchy_data, modules_used)

        assert "## Contents" not in md

    def test_sequence_call_hyperlinks(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "Call_Subsequence_A" in md
        assert "Call_Subsequence_B" in md

    def test_precondition_in_output(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "Locals.Local_Var_1 > 0" in md

    def test_comment_in_output(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "Initialize resources" in md

    def test_variables_appendix_engineer(self, engine, seq_file):
        ext = Extractor(engine, include_scopes=["Locals", "Parameters"])
        ext.analyze_hierarchy(str(seq_file))
        hierarchy_data, modules_used = ext.extractor.hierarchy_data, ext.extractor.modules_used

        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, modules_used)

        assert "## Variables" in md
        assert "MainSequence" in md
        assert "Local_Var_1" in md
        assert "Param_A" in md

    def test_variables_appendix_business(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter(profile="business")
        md = fmt.format(hierarchy_data, modules_used)

        assert "## Variables" not in md

    def test_callbacks_sorted_chronologically(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter()
        md = fmt.format(hierarchy_data, modules_used)

        seq_file_pos = md.index("# test_output")
        callbacks_section = md[seq_file_pos:]

        load_pos = callbacks_section.index("SequenceFileLoad")
        setup_pos = callbacks_section.index("ProcessSetup")
        post_pos = callbacks_section.index("PostMainSequence")

        assert post_pos < setup_pos < load_pos

    def test_markdown_ends_with_newline(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter()
        md = fmt.format(hierarchy_data, modules_used)

        assert md.endswith("\n")
        assert not md.endswith("\n\n")

    def test_no_multiple_blank_lines(self, extracted_data):
        hierarchy_data, modules_used = extracted_data
        fmt = Formatter()
        md = fmt.format(hierarchy_data, modules_used)

        assert "\n\n\n" not in md

    def test_detailed_popup_messages(self):
        steps = [
            {
                "name": "Popup 1",
                "type": "MessagePopup",
                "expressions": {
                    "title": '"Warning Title"',
                    "message": '"This is a message description."',
                    "time_to_wait": "5.0",
                },
            },
            {
                "name": "Popup 2",
                "type": "MessagePopup",
                "expressions": {
                    "title": '"No Timeout Popup"',
                    "message": '"Will wait forever."',
                    "time_to_wait": "0",
                },
            },
        ]
        hierarchy_data = [
            {
                "name": "test_file.seq",
                "path": r"C:\test_file.seq",
                "sequences": [
                    {
                        "name": "MainSequence",
                        "category": "Subsequence",
                        "comment": "",
                        "variables": {},
                        "step_groups": {"Main": steps},
                    },
                ],
            },
        ]
        fmt = Formatter(profile="engineer", include_flowcharts=True, detailed_popup_messages=True)
        md = fmt.format(hierarchy_data, {})

        assert "Warning Title" in md
        assert "This is a message description" in md
        assert "Timeout: 5.0s" in md
        assert "No Timeout Popup" in md

    def test_estimate_software_delays(self):
        hierarchy_data = [
            {
                "name": "test_file.seq",
                "path": r"C:\test_file.seq",
                "estimated_software_delay": 7.5,
                "sequences": [
                    {
                        "name": "MainSequence",
                        "category": "Subsequence",
                        "comment": "",
                        "variables": {},
                        "estimated_software_delay": 7.5,
                        "step_groups": {
                            "Main": [
                                {
                                    "name": "Step 1",
                                    "type": "Action",
                                },
                            ],
                        },
                    },
                ],
            },
        ]
        fmt = Formatter(profile="engineer")
        md = fmt.format(hierarchy_data, {})

        assert "**Total Minimum Software Delay:** 7.5s" in md
        assert "**Minimum Software Delay:** 7.5s" in md

    def test_rich_popup_buttons(self):
        steps = [
            {
                "name": "Investigation Need",
                "type": "MessagePopup",
                "expressions": {
                    "title": '"Investigation Need"',
                    "message": '"Do you want to proceed?"',
                    "button1": '"OK"',
                    "button2": '"NOK"',
                    "button3": '""',
                    "button4": '"Retry"',
                    "timer_button": "2",
                    "default_button": "2",
                    "time_to_wait": "15",
                },
            },
            {
                "name": "Dummy Step",
                "type": "Action",
            },
        ]
        hierarchy_data = [
            {
                "name": "test_file.seq",
                "path": r"C:\test_file.seq",
                "sequences": [
                    {
                        "name": "MainSequence",
                        "category": "Subsequence",
                        "step_groups": {"Main": steps},
                    },
                ],
            },
        ]
        fmt = Formatter(profile="engineer", include_flowcharts=True, detailed_popup_messages=True)
        md = fmt.format(hierarchy_data, {})

        assert "[1: OK] [2: NOK] [4: Retry]" in md
        assert "Default: 2" in md
        assert "Timeout: 15s \u2192 triggers [2]" in md

    def test_nested_flow_control(self):
        steps = [
            {"name": "If 1", "type": "NI_Flow_If", "description": "Cond 1"},
            {"name": "If 2", "type": "NI_Flow_If", "description": "Cond 2"},
            {"name": "If 3", "type": "NI_Flow_If", "description": "Cond 3"},
            {"name": "Action", "type": "Action"},
            {"name": "End 3", "type": "NI_Flow_End"},
            {"name": "End 2", "type": "NI_Flow_End"},
            {"name": "End 1", "type": "NI_Flow_End"},
            {"name": "Select", "type": "NI_Flow_Select", "description": "Select Cond"},
            {"name": "Case 1", "type": "NI_Flow_Case", "description": "Item 1"},
            {"name": "Case Action", "type": "Action"},
            {"name": "End Case 1", "type": "NI_Flow_End"},
            {"name": "Case 2", "type": "NI_Flow_Case", "description": "Item 2"},
            {"name": "Case Action 2", "type": "Action"},
            {"name": "End Case 2", "type": "NI_Flow_End"},
            {"name": "End Select", "type": "NI_Flow_End"},
        ]
        hierarchy_data = [
            {
                "name": "test_file.seq",
                "path": r"C:\test_file.seq",
                "sequences": [
                    {
                        "name": "MainSequence",
                        "category": "Subsequence",
                        "step_groups": {"Main": steps},
                    },
                ],
            },
        ]
        fmt = Formatter(profile="engineer", include_flowcharts=True)
        md = fmt.format(hierarchy_data, {})

        # Verify the structure has Mermaid block without hanging components
        assert "flowchart TD" in md
        # The select block should have a fallthrough for 'no match'
        assert '|"no match"|' in md

    def test_loop_break_flow_control(self):
        steps = [
            {"name": "While True", "type": "NI_Flow_While", "description": "True"},
            {"name": "Update LED", "type": "Statement"},
            {"name": "Break Loop", "type": "NI_Flow_Break"},
            {"name": "End While", "type": "NI_Flow_End"},
        ]
        hierarchy_data = [
            {
                "name": "test_loop.seq",
                "path": r"C:\test_loop.seq",
                "sequences": [
                    {
                        "name": "MainSequence",
                        "category": "Subsequence",
                        "step_groups": {"Main": steps},
                    },
                ],
            },
        ]
        fmt = Formatter(profile="engineer", include_flowcharts=True)
        md = fmt.format(hierarchy_data, {})

        # Verify that break routes to the end correctly
        assert "flowchart TD" in md
        assert '|"break"|' in md

    def test_path_and_logo_options(self, extracted_data):
        hierarchy_data, modules_used = extracted_data

        # Test default (include_path=False, company_logo=None)
        fmt_default = Formatter(profile="engineer")
        md_default = fmt_default.format(hierarchy_data, modules_used)
        assert "test_output.seq" not in md_default
        assert "![Company Logo]" not in md_default

        # Test show_paths=True
        fmt_path = Formatter(profile="engineer", show_paths=True)
        md_path = fmt_path.format(hierarchy_data, modules_used)
        assert "test_output.seq" in md_path

        # Test company_logo
        fmt_logo = Formatter(profile="engineer", company_logo="logo.png")
        md_logo = fmt_logo.format(hierarchy_data, modules_used)
        assert "![Company Logo](logo.png)" in md_logo
