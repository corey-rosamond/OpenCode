"""Task tools for spawning subagents.

This module provides the TaskTool which allows the LLM to spawn
specialized agents for complex tasks.
"""

from code_forge.tools.registry import ToolRegistry
from code_forge.tools.task.task import TaskTool

__all__ = ["TaskTool", "register_task_tools"]


def register_task_tools() -> None:
    """Register task tools with the registry."""
    registry = ToolRegistry()
    registry.register(TaskTool())
