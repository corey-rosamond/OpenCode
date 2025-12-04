"""Tests for Plan mode."""

from datetime import datetime

import pytest

from opencode.modes.base import ModeContext, ModeName
from opencode.modes.plan import Plan, PlanMode, PlanStep


class TestPlanStep:
    """Tests for PlanStep dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic step creation."""
        step = PlanStep(number=1, description="First step")
        assert step.number == 1
        assert step.description == "First step"
        assert step.completed is False
        assert step.files == []
        assert step.dependencies == []
        assert step.complexity == "medium"
        assert step.substeps == []

    def test_with_files(self) -> None:
        """Test step with files."""
        step = PlanStep(
            number=1,
            description="Update files",
            files=["file1.py", "file2.py"],
        )
        assert step.files == ["file1.py", "file2.py"]

    def test_with_dependencies(self) -> None:
        """Test step with dependencies."""
        step = PlanStep(
            number=2,
            description="Depends on step 1",
            dependencies=[1],
        )
        assert step.dependencies == [1]

    def test_with_complexity(self) -> None:
        """Test step with complexity."""
        step = PlanStep(number=1, description="Complex", complexity="high")
        assert step.complexity == "high"

    def test_to_markdown_basic(self) -> None:
        """Test basic markdown conversion."""
        step = PlanStep(number=1, description="First step")
        md = step.to_markdown()
        assert "1. [ ] First step" in md

    def test_to_markdown_completed(self) -> None:
        """Test completed step markdown."""
        step = PlanStep(number=1, description="Done", completed=True)
        md = step.to_markdown()
        assert "[x]" in md

    def test_to_markdown_with_files(self) -> None:
        """Test markdown with files."""
        step = PlanStep(
            number=1,
            description="Step",
            files=["a.py", "b.py"],
        )
        md = step.to_markdown()
        assert "Files: a.py, b.py" in md

    def test_to_markdown_with_dependencies(self) -> None:
        """Test markdown with dependencies."""
        step = PlanStep(
            number=2,
            description="Step",
            dependencies=[1],
        )
        md = step.to_markdown()
        assert "Dependencies: Step 1" in md

    def test_to_markdown_with_complexity(self) -> None:
        """Test markdown with complexity."""
        step = PlanStep(
            number=1,
            description="Step",
            complexity="high",
        )
        md = step.to_markdown()
        assert "Complexity: High" in md

    def test_to_markdown_nested(self) -> None:
        """Test nested step markdown."""
        substep = PlanStep(number=1, description="Substep")
        step = PlanStep(
            number=1,
            description="Parent",
            substeps=[substep],
        )
        md = step.to_markdown()
        assert "Parent" in md
        assert "Substep" in md

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        step = PlanStep(
            number=1,
            description="Test",
            files=["a.py"],
            dependencies=[],
            complexity="low",
            completed=True,
        )
        data = step.to_dict()
        assert data["number"] == 1
        assert data["description"] == "Test"
        assert data["files"] == ["a.py"]
        assert data["completed"] is True
        assert data["complexity"] == "low"

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "number": 2,
            "description": "Step 2",
            "files": ["b.py"],
            "dependencies": [1],
            "complexity": "high",
            "completed": True,
            "substeps": [],
        }
        step = PlanStep.from_dict(data)
        assert step.number == 2
        assert step.description == "Step 2"
        assert step.files == ["b.py"]
        assert step.dependencies == [1]
        assert step.complexity == "high"
        assert step.completed is True

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = PlanStep(
            number=1,
            description="Original",
            files=["test.py"],
            dependencies=[],
            complexity="medium",
            completed=False,
            substeps=[PlanStep(number=1, description="Sub")],
        )
        restored = PlanStep.from_dict(original.to_dict())
        assert restored.number == original.number
        assert restored.description == original.description
        assert len(restored.substeps) == 1


class TestPlan:
    """Tests for Plan dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic plan creation."""
        plan = Plan(
            title="Test Plan",
            summary="Testing",
            steps=[PlanStep(number=1, description="Step 1")],
        )
        assert plan.title == "Test Plan"
        assert plan.summary == "Testing"
        assert len(plan.steps) == 1
        assert plan.considerations == []
        assert plan.success_criteria == []

    def test_with_considerations(self) -> None:
        """Test plan with considerations."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[],
            considerations=["Risk 1", "Risk 2"],
        )
        assert plan.considerations == ["Risk 1", "Risk 2"]

    def test_with_success_criteria(self) -> None:
        """Test plan with success criteria."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[],
            success_criteria=["Tests pass", "Coverage > 90%"],
        )
        assert plan.success_criteria == ["Tests pass", "Coverage > 90%"]

    def test_progress_empty(self) -> None:
        """Test progress with no steps."""
        plan = Plan(title="Test", summary="Test", steps=[])
        assert plan.progress == (0, 0)

    def test_progress_none_completed(self) -> None:
        """Test progress with no completed steps."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="A"),
                PlanStep(number=2, description="B"),
            ],
        )
        assert plan.progress == (0, 2)

    def test_progress_some_completed(self) -> None:
        """Test progress with some completed steps."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="A", completed=True),
                PlanStep(number=2, description="B"),
                PlanStep(number=3, description="C", completed=True),
            ],
        )
        assert plan.progress == (2, 3)

    def test_progress_percentage_empty(self) -> None:
        """Test progress percentage with no steps."""
        plan = Plan(title="Test", summary="Test", steps=[])
        assert plan.progress_percentage == 0.0

    def test_progress_percentage_partial(self) -> None:
        """Test progress percentage with some completed."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="A", completed=True),
                PlanStep(number=2, description="B"),
            ],
        )
        assert plan.progress_percentage == 50.0

    def test_mark_step_complete_success(self) -> None:
        """Test marking step complete."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="A"),
                PlanStep(number=2, description="B"),
            ],
        )
        original_updated = plan.updated_at

        result = plan.mark_step_complete(1)

        assert result is True
        assert plan.steps[0].completed is True
        assert plan.steps[1].completed is False
        assert plan.updated_at >= original_updated

    def test_mark_step_complete_not_found(self) -> None:
        """Test marking non-existent step."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[PlanStep(number=1, description="A")],
        )
        result = plan.mark_step_complete(99)
        assert result is False

    def test_to_markdown(self) -> None:
        """Test full markdown conversion."""
        plan = Plan(
            title="Test Plan",
            summary="Testing markdown output",
            steps=[
                PlanStep(number=1, description="First"),
                PlanStep(number=2, description="Second"),
            ],
            considerations=["Risk 1"],
            success_criteria=["Tests pass"],
        )
        md = plan.to_markdown()

        assert "## Plan: Test Plan" in md
        assert "### Summary" in md
        assert "Testing markdown output" in md
        assert "### Steps" in md
        assert "1. [ ] First" in md
        assert "2. [ ] Second" in md
        assert "### Considerations" in md
        assert "- Risk 1" in md
        assert "### Success Criteria" in md
        assert "- Tests pass" in md

    def test_to_todos(self) -> None:
        """Test conversion to todo items."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="First step"),
                PlanStep(number=2, description="Second step", completed=True),
            ],
        )
        todos = plan.to_todos()

        assert len(todos) == 2
        assert todos[0]["content"] == "First step"
        assert todos[0]["status"] == "pending"
        assert "activeForm" in todos[0]
        assert todos[1]["status"] == "completed"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        plan = Plan(
            title="Test",
            summary="Summary",
            steps=[PlanStep(number=1, description="Step")],
            considerations=["Risk"],
            success_criteria=["Pass"],
        )
        data = plan.to_dict()

        assert data["title"] == "Test"
        assert data["summary"] == "Summary"
        assert len(data["steps"]) == 1
        assert data["considerations"] == ["Risk"]
        assert data["success_criteria"] == ["Pass"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "title": "Test",
            "summary": "Summary",
            "steps": [{"number": 1, "description": "Step"}],
            "considerations": ["Risk"],
            "success_criteria": ["Pass"],
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00",
        }
        plan = Plan.from_dict(data)

        assert plan.title == "Test"
        assert plan.summary == "Summary"
        assert len(plan.steps) == 1
        assert plan.considerations == ["Risk"]

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = Plan(
            title="Original",
            summary="Test",
            steps=[
                PlanStep(number=1, description="A"),
                PlanStep(number=2, description="B"),
            ],
            considerations=["Risk"],
            success_criteria=["Pass"],
        )
        restored = Plan.from_dict(original.to_dict())

        assert restored.title == original.title
        assert restored.summary == original.summary
        assert len(restored.steps) == len(original.steps)
        assert restored.considerations == original.considerations


class TestPlanMode:
    """Tests for PlanMode class."""

    @pytest.fixture
    def mode(self) -> PlanMode:
        """Create plan mode for tests."""
        return PlanMode()

    @pytest.fixture
    def context(self) -> ModeContext:
        """Create test context."""
        messages: list[str] = []
        return ModeContext(output=lambda m: messages.append(m))

    def test_name(self, mode: PlanMode) -> None:
        """Test mode name."""
        assert mode.name == ModeName.PLAN

    def test_default_config(self, mode: PlanMode) -> None:
        """Test default configuration."""
        assert mode.config.name == ModeName.PLAN
        assert mode.config.description == "Structured planning mode"
        assert "PLAN MODE" in mode.config.system_prompt_addition

    def test_initial_state(self, mode: PlanMode) -> None:
        """Test initial state."""
        assert mode.is_active is False
        assert mode.current_plan is None

    def test_activate(self, mode: PlanMode, context: ModeContext) -> None:
        """Test mode activation."""
        mode.activate(context)
        assert mode.is_active is True

    def test_deactivate(self, mode: PlanMode, context: ModeContext) -> None:
        """Test mode deactivation."""
        mode.activate(context)

        plan = Plan(title="Test", summary="Test", steps=[])
        mode.set_plan(plan)

        mode.deactivate(context)

        assert mode.is_active is False
        assert mode.current_plan is None
        # Plan should be saved to last_plan
        assert "last_plan" in mode._state.data

    def test_should_auto_activate_plan_request(self, mode: PlanMode) -> None:
        """Test auto-activation for planning request."""
        assert mode.should_auto_activate("Plan how to add authentication") is True
        assert mode.should_auto_activate("Plan for implementing cache") is True

    def test_should_auto_activate_break_down(self, mode: PlanMode) -> None:
        """Test auto-activation for break down request."""
        assert mode.should_auto_activate("Break down the task") is True
        assert mode.should_auto_activate("Breakdown the feature") is True

    def test_should_auto_activate_steps(self, mode: PlanMode) -> None:
        """Test auto-activation for steps request."""
        assert mode.should_auto_activate("Steps to implement") is True
        assert mode.should_auto_activate("Step for adding tests") is True

    def test_should_not_auto_activate_normal(self, mode: PlanMode) -> None:
        """Test no auto-activation for normal messages."""
        assert mode.should_auto_activate("Hello world") is False
        assert mode.should_auto_activate("Fix the bug") is False
        assert mode.should_auto_activate("Write a function") is False

    def test_set_and_get_plan(self, mode: PlanMode) -> None:
        """Test setting and getting plan."""
        plan = Plan(
            title="Test Plan",
            summary="Testing",
            steps=[PlanStep(number=1, description="Step")],
        )
        mode.set_plan(plan)

        assert mode.get_plan() is plan
        assert mode.current_plan is plan

    def test_show_plan_none(self, mode: PlanMode) -> None:
        """Test showing plan when none exists."""
        result = mode.show_plan()
        assert "No plan" in result

    def test_show_plan_exists(self, mode: PlanMode) -> None:
        """Test showing existing plan."""
        plan = Plan(
            title="Test Plan",
            summary="Testing",
            steps=[PlanStep(number=1, description="Step")],
        )
        mode.set_plan(plan)

        result = mode.show_plan()
        assert "Test Plan" in result

    def test_execute_plan_empty(self, mode: PlanMode) -> None:
        """Test executing with no plan."""
        todos = mode.execute_plan()
        assert todos == []

    def test_execute_plan(self, mode: PlanMode) -> None:
        """Test executing plan."""
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[
                PlanStep(number=1, description="First"),
                PlanStep(number=2, description="Second"),
            ],
        )
        mode.set_plan(plan)

        todos = mode.execute_plan()

        assert len(todos) == 2
        assert todos[0]["content"] == "First"
        assert todos[1]["content"] == "Second"

    def test_cancel_plan(self, mode: PlanMode) -> None:
        """Test canceling plan."""
        plan = Plan(title="Test", summary="Test", steps=[])
        mode.set_plan(plan)

        mode.cancel_plan()

        assert mode.current_plan is None
        assert "current_plan" not in mode._state.data

    def test_save_state_with_plan(
        self, mode: PlanMode, context: ModeContext
    ) -> None:
        """Test saving state with plan."""
        mode.activate(context)
        plan = Plan(
            title="Test",
            summary="Test",
            steps=[PlanStep(number=1, description="Step")],
        )
        mode.set_plan(plan)

        state = mode.save_state()

        assert state["active"] is True
        assert "current_plan" in state["data"]
        assert state["data"]["current_plan"]["title"] == "Test"

    def test_restore_state_with_plan(self, mode: PlanMode) -> None:
        """Test restoring state with plan."""
        state = {
            "mode_name": "plan",
            "active": True,
            "data": {
                "current_plan": {
                    "title": "Restored",
                    "summary": "From state",
                    "steps": [{"number": 1, "description": "Step"}],
                    "considerations": [],
                    "success_criteria": [],
                    "created_at": "2025-01-01T12:00:00",
                    "updated_at": "2025-01-01T12:00:00",
                }
            },
        }

        mode.restore_state(state)

        assert mode.current_plan is not None
        assert mode.current_plan.title == "Restored"
