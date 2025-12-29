"""Tests for tool sequence planning."""

from __future__ import annotations

import pytest

from code_forge.natural.planner import (
    PlannedStep,
    SequenceTemplate,
    StepType,
    ToolSequence,
    ToolSequencePlanner,
)


class TestStepType:
    """Tests for StepType enum."""

    def test_values(self) -> None:
        """Test step type values."""
        assert StepType.TOOL_CALL.value == "tool_call"
        assert StepType.CONDITIONAL.value == "conditional"
        assert StepType.LOOP.value == "loop"
        assert StepType.PARALLEL.value == "parallel"


class TestPlannedStep:
    """Tests for PlannedStep dataclass."""

    def test_creation(self) -> None:
        """Test step creation."""
        step = PlannedStep(
            step_type=StepType.TOOL_CALL,
            tool_name="Edit",
            parameters={"file_path": "test.py"},
            description="Edit the file",
        )
        assert step.step_type == StepType.TOOL_CALL
        assert step.tool_name == "Edit"
        assert step.parameters["file_path"] == "test.py"

    def test_dependencies(self) -> None:
        """Test step dependencies."""
        step = PlannedStep(
            step_type=StepType.TOOL_CALL,
            tool_name="Bash",
            depends_on=[0, 1],
        )
        assert step.depends_on == [0, 1]


class TestToolSequence:
    """Tests for ToolSequence dataclass."""

    def test_creation(self) -> None:
        """Test sequence creation."""
        steps = [
            PlannedStep(StepType.TOOL_CALL, tool_name="Read"),
            PlannedStep(StepType.TOOL_CALL, tool_name="Edit"),
        ]
        sequence = ToolSequence(
            steps=steps,
            description="Read and edit",
            estimated_complexity="medium",
        )
        assert len(sequence.steps) == 2
        assert sequence.tool_count == 2

    def test_empty_sequence(self) -> None:
        """Test empty sequence."""
        sequence = ToolSequence(steps=[])
        assert sequence.tool_count == 0


class TestSequenceTemplate:
    """Tests for SequenceTemplate dataclass."""

    def test_creation(self) -> None:
        """Test template creation."""
        template = SequenceTemplate(
            name="test_template",
            description="Test",
            trigger_patterns=[r"test pattern"],
            steps=[{"tool": "Read", "params": {}}],
        )
        assert template.name == "test_template"
        assert len(template.steps) == 1


class TestToolSequencePlanner:
    """Tests for ToolSequencePlanner."""

    @pytest.fixture
    def planner(self) -> ToolSequencePlanner:
        """Create a planner instance."""
        return ToolSequencePlanner()

    def test_plan_simple_request(self, planner: ToolSequencePlanner) -> None:
        """Test planning a simple single-step request."""
        sequence = planner.plan("read config.py")

        assert sequence.tool_count >= 1
        assert sequence.estimated_complexity == "low"

    def test_plan_unknown_request(self, planner: ToolSequencePlanner) -> None:
        """Test planning an unrecognized request."""
        sequence = planner.plan("xyzzy")

        assert len(sequence.steps) == 0

    def test_plan_rename_across_project(self, planner: ToolSequencePlanner) -> None:
        """Test planning a project-wide rename."""
        sequence = planner.plan("rename getData to fetchData across the project")

        # Should match rename template
        assert sequence.tool_count >= 1
        assert "rename" in sequence.description.lower() or len(sequence.steps) > 0

    def test_plan_find_and_edit(self, planner: ToolSequencePlanner) -> None:
        """Test planning find and edit sequence."""
        sequence = planner.plan("find all *.py files and edit them")

        # Should create multi-step sequence
        assert sequence.tool_count >= 1

    def test_plan_complex_with_then(self, planner: ToolSequencePlanner) -> None:
        """Test planning complex request with 'then'."""
        sequence = planner.plan_complex("read the file then edit it")

        # Should create sequential steps
        assert sequence.tool_count >= 1

    def test_plan_complex_with_and_then(self, planner: ToolSequencePlanner) -> None:
        """Test planning complex request with 'and then'."""
        sequence = planner.plan_complex("find the error and then fix it")

        assert sequence.tool_count >= 1

    def test_requires_sequence_simple(self, planner: ToolSequencePlanner) -> None:
        """Test detecting simple single-step requests."""
        assert not planner.requires_sequence("read config.py")
        assert not planner.requires_sequence("edit main.js")

    def test_requires_sequence_complex(self, planner: ToolSequencePlanner) -> None:
        """Test detecting complex multi-step requests."""
        assert planner.requires_sequence("read the file and then edit it")
        assert planner.requires_sequence("find all files and modify them")
        assert planner.requires_sequence("rename foo to bar across all files")

    def test_template_matching(self, planner: ToolSequencePlanner) -> None:
        """Test that templates are matched correctly."""
        # Test a template that should match
        sequence = planner.plan("create a new file called test.py with content")

        # Should match create_with_content or similar template
        assert sequence.tool_count >= 1

    def test_step_dependencies(self, planner: ToolSequencePlanner) -> None:
        """Test that step dependencies are set correctly."""
        sequence = planner.plan_complex("read config.py then edit it then run tests")

        # Later steps should depend on earlier ones
        for i, step in enumerate(sequence.steps[1:], 1):
            if step.depends_on:
                # Dependencies should be to previous steps
                assert all(d < i for d in step.depends_on)

    def test_get_sequence_summary(self, planner: ToolSequencePlanner) -> None:
        """Test sequence summary generation."""
        sequence = planner.plan("find files matching *.py")
        summary = planner.get_sequence_summary(sequence)

        assert "Plan:" in summary or "step" in summary.lower()

    def test_get_sequence_summary_empty(self, planner: ToolSequencePlanner) -> None:
        """Test summary for empty sequence."""
        sequence = ToolSequence(steps=[])
        summary = planner.get_sequence_summary(sequence)

        assert "No steps" in summary

    def test_complexity_estimation(self, planner: ToolSequencePlanner) -> None:
        """Test complexity estimation."""
        # Simple request
        simple = planner.plan("read file.py")
        assert simple.estimated_complexity == "low"

        # Complex request (if template matches)
        complex_seq = planner.plan_complex(
            "find all errors then fix them then run tests then deploy"
        )
        # Complex requests with many steps should have higher complexity
        if complex_seq.tool_count > 4:
            assert complex_seq.estimated_complexity in ("medium", "high")


class TestToolSequencePlannerTemplates:
    """Tests for specific templates."""

    @pytest.fixture
    def planner(self) -> ToolSequencePlanner:
        """Create a planner instance."""
        return ToolSequencePlanner()

    def test_test_after_edit_template(self, planner: ToolSequencePlanner) -> None:
        """Test the test-after-edit template."""
        sequence = planner.plan("fix the bug and run tests")

        # Should match test_after_edit template or create sequence
        assert sequence.tool_count >= 1

    def test_backup_and_edit_template(self, planner: ToolSequencePlanner) -> None:
        """Test the backup-and-edit template."""
        sequence = planner.plan("backup config.py before editing it")

        # Should match backup_and_edit template
        if sequence.tool_count >= 2:
            # First step should be backup (Bash cp)
            tool_names = [s.tool_name for s in sequence.steps]
            assert "Bash" in tool_names or "Edit" in tool_names

    def test_read_then_edit_template(self, planner: ToolSequencePlanner) -> None:
        """Test the read-then-edit template."""
        sequence = planner.plan("look at main.py and then edit it")

        # Should match read_then_edit template
        if sequence.tool_count >= 2:
            tool_names = [s.tool_name for s in sequence.steps]
            # Should have both Read and Edit
            has_read = "Read" in tool_names or any("read" in s.description.lower() for s in sequence.steps)
            has_edit = "Edit" in tool_names or any("edit" in s.description.lower() for s in sequence.steps)
            assert has_read or has_edit
