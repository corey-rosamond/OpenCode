"""
Plan mode implementation.

Provides structured planning capabilities with task breakdown,
dependency tracking, and plan execution support.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import Mode, ModeConfig, ModeContext, ModeName
from .prompts import PLAN_MODE_PROMPT


@dataclass
class PlanStep:
    """A step in a plan.

    Attributes:
        number: Step number (1-indexed)
        description: What this step accomplishes
        substeps: Nested substeps if any
        completed: Whether step is done
        files: Files to be modified
        dependencies: Step numbers this depends on
        complexity: Relative complexity estimate
    """

    number: int
    description: str
    substeps: list["PlanStep"] = field(default_factory=list)
    completed: bool = False
    files: list[str] = field(default_factory=list)
    dependencies: list[int] = field(default_factory=list)
    complexity: str = "medium"  # low, medium, high

    def to_markdown(self, indent: int = 0) -> str:
        """Convert step to markdown format.

        Args:
            indent: Indentation level for nested steps

        Returns:
            Markdown representation of step
        """
        prefix = "  " * indent
        check = "x" if self.completed else " "
        lines = [f"{prefix}{self.number}. [{check}] {self.description}"]

        if self.files:
            lines.append(f"{prefix}   - Files: {', '.join(self.files)}")
        if self.dependencies:
            deps = ", ".join(f"Step {d}" for d in self.dependencies)
            lines.append(f"{prefix}   - Dependencies: {deps}")
        if self.complexity:
            lines.append(f"{prefix}   - Complexity: {self.complexity.title()}")

        for substep in self.substeps:
            lines.append(substep.to_markdown(indent + 1))

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of step
        """
        return {
            "number": self.number,
            "description": self.description,
            "substeps": [s.to_dict() for s in self.substeps],
            "completed": self.completed,
            "files": self.files,
            "dependencies": self.dependencies,
            "complexity": self.complexity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        """Deserialize from dictionary.

        Args:
            data: Dictionary to deserialize from

        Returns:
            PlanStep instance
        """
        return cls(
            number=data["number"],
            description=data["description"],
            substeps=[cls.from_dict(s) for s in data.get("substeps", [])],
            completed=data.get("completed", False),
            files=data.get("files", []),
            dependencies=data.get("dependencies", []),
            complexity=data.get("complexity", "medium"),
        )


@dataclass
class Plan:
    """A structured plan.

    Represents a complete plan with steps, considerations,
    and success criteria.

    Attributes:
        title: Plan title
        summary: Brief summary of the plan
        steps: List of plan steps
        considerations: Important considerations or risks
        success_criteria: How to verify success
        created_at: When plan was created
        updated_at: When plan was last updated
    """

    title: str
    summary: str
    steps: list[PlanStep]
    considerations: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Convert plan to markdown format.

        Returns:
            Markdown representation of plan
        """
        lines = [
            f"## Plan: {self.title}",
            "",
            "### Summary",
            self.summary,
            "",
            "### Steps",
        ]

        for step in self.steps:
            lines.append(step.to_markdown())

        if self.considerations:
            lines.extend([
                "",
                "### Considerations",
            ])
            for c in self.considerations:
                lines.append(f"- {c}")

        if self.success_criteria:
            lines.extend([
                "",
                "### Success Criteria",
            ])
            for sc in self.success_criteria:
                lines.append(f"- {sc}")

        return "\n".join(lines)

    def to_todos(self) -> list[dict[str, Any]]:
        """Convert plan steps to todo items.

        Returns:
            List of todo dictionaries
        """
        todos = []
        for step in self.steps:
            todos.append({
                "content": step.description,
                "status": "completed" if step.completed else "pending",
                "activeForm": f"Working on: {step.description}",
            })
        return todos

    @property
    def progress(self) -> tuple[int, int]:
        """Get (completed, total) step counts.

        Returns:
            Tuple of (completed count, total count)
        """
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.completed)
        return completed, total

    @property
    def progress_percentage(self) -> float:
        """Get completion percentage.

        Returns:
            Percentage of steps completed (0-100)
        """
        completed, total = self.progress
        return (completed / total * 100) if total > 0 else 0.0

    def mark_step_complete(self, step_number: int) -> bool:
        """Mark a step as complete.

        Args:
            step_number: Number of step to mark complete

        Returns:
            True if step was found and marked, False otherwise
        """
        for step in self.steps:
            if step.number == step_number:
                step.completed = True
                self.updated_at = datetime.now()
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of plan
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "considerations": self.considerations,
            "success_criteria": self.success_criteria,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        """Deserialize from dictionary.

        Args:
            data: Dictionary to deserialize from

        Returns:
            Plan instance
        """
        return cls(
            title=data["title"],
            summary=data["summary"],
            steps=[PlanStep.from_dict(s) for s in data["steps"]],
            considerations=data.get("considerations", []),
            success_criteria=data.get("success_criteria", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


# Patterns for detecting planning requests
PLANNING_PATTERNS = [
    r"\bplan\b.*\b(how|to|for)\b",
    r"\bbreak\s*down\b",
    r"\bsteps?\s+(to|for)\b",
    r"\bstrategy\s+for\b",
    r"\bapproach\s+to\b",
    r"\bdesign\b.*\bimplementation\b",
    r"\barchitect\b",
    r"\broadmap\b",
]


class PlanMode(Mode):
    """Planning mode for structured task planning.

    Modifies assistant behavior to focus on creating
    actionable, structured plans before implementation.
    """

    def __init__(self, config: ModeConfig | None = None) -> None:
        """Initialize plan mode.

        Args:
            config: Optional mode configuration
        """
        super().__init__(config)
        self.current_plan: Plan | None = None

    @property
    def name(self) -> ModeName:
        """Return mode name.

        Returns:
            ModeName.PLAN
        """
        return ModeName.PLAN

    def _default_config(self) -> ModeConfig:
        """Return default configuration for plan mode.

        Returns:
            ModeConfig with plan mode prompt
        """
        return ModeConfig(
            name=ModeName.PLAN,
            description="Structured planning mode",
            system_prompt_addition=PLAN_MODE_PROMPT,
        )

    def activate(self, context: ModeContext) -> None:
        """Enter plan mode.

        Args:
            context: Mode context
        """
        super().activate(context)
        context.output("Entered plan mode. I'll create a structured plan.")
        context.output("Use /plan execute to implement, /plan cancel to abort.")

    def deactivate(self, context: ModeContext) -> None:
        """Exit plan mode.

        Args:
            context: Mode context
        """
        # Save plan before super().deactivate clears state.data
        last_plan_data = None
        if self.current_plan:
            last_plan_data = self.current_plan.to_dict()
        self.current_plan = None
        super().deactivate(context)
        # Restore last_plan after clearing
        if last_plan_data:
            self._state.data["last_plan"] = last_plan_data
        context.output("Exited plan mode.")

    def should_auto_activate(self, message: str) -> bool:
        """Detect planning requests in message.

        Args:
            message: User message to check

        Returns:
            True if message appears to be a planning request
        """
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in PLANNING_PATTERNS)

    def set_plan(self, plan: Plan) -> None:
        """Set the current plan.

        Args:
            plan: Plan to set as current
        """
        self.current_plan = plan
        self._state.data["current_plan"] = plan.to_dict()

    def get_plan(self) -> Plan | None:
        """Get current plan.

        Returns:
            Current plan or None
        """
        return self.current_plan

    def show_plan(self) -> str:
        """Get plan display text.

        Returns:
            Markdown representation of plan or message if no plan
        """
        if not self.current_plan:
            return "No plan created yet."
        return self.current_plan.to_markdown()

    def execute_plan(self) -> list[dict[str, Any]]:
        """Convert plan to executable todos.

        Returns:
            List of todo dictionaries
        """
        if not self.current_plan:
            return []
        return self.current_plan.to_todos()

    def cancel_plan(self) -> None:
        """Cancel current plan."""
        self.current_plan = None
        self._state.data.pop("current_plan", None)

    def save_state(self) -> dict[str, Any]:
        """Save plan mode state.

        Returns:
            Dictionary containing serialized state
        """
        state = super().save_state()
        if self.current_plan:
            state["data"]["current_plan"] = self.current_plan.to_dict()
        return state

    def restore_state(self, data: dict[str, Any]) -> None:
        """Restore plan mode state.

        Args:
            data: Dictionary containing serialized state
        """
        super().restore_state(data)
        plan_data = self._state.data.get("current_plan")
        if plan_data:
            self.current_plan = Plan.from_dict(plan_data)
