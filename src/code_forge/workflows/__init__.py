"""Multi-agent workflow orchestration system.

This module provides a workflow system for coordinating multiple specialized
agents in complex, multi-step development tasks. Workflows define sequences
of agent executions with dependencies, conditions, and parallel execution.

Key Components:
    - WorkflowDefinition: Workflow specification with steps and metadata
    - WorkflowExecutor: Executes workflows with proper orchestration
    - WorkflowGraph: DAG representation for dependency management
    - Templates: Pre-built workflows for common tasks

Example:
    >>> from code_forge.workflows import Workflow, WorkflowExecutor
    >>> workflow = Workflow.from_yaml("pr_review.yaml")
    >>> executor = WorkflowExecutor()
    >>> result = await executor.execute(workflow)
"""

from __future__ import annotations

__all__ = [
    # Models
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowState",
    "WorkflowStatus",
    "StepResult",
    "WorkflowResult",
    # Graph
    "WorkflowGraph",
    "GraphValidator",
    "TopologicalSorter",
    # State Management
    "StateManager",
    "CheckpointManager",
    "StateManagementError",
    "CheckpointNotFoundError",
    "CheckpointCorruptedError",
    # Execution
    "WorkflowExecutor",
    "StepExecutor",
    "WorkflowExecutionError",
    "StepExecutionError",
    # Templates & Registry
    "WorkflowTemplateRegistry",
    # Parsing
    "YAMLWorkflowParser",
    "PythonWorkflowBuilder",
    # Commands
    "WorkflowCommand",
    "WorkflowListCommand",
    "WorkflowRunCommand",
    "WorkflowStatusCommand",
    "WorkflowResumeCommand",
    "WorkflowCancelCommand",
    # Tools
    "WorkflowTool",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import workflow components to avoid circular dependencies."""
    if name in __all__:
        # Import on first access
        if name in ["WorkflowDefinition", "WorkflowStep", "WorkflowState", "WorkflowStatus", "StepResult", "WorkflowResult"]:
            from code_forge.workflows.models import (
                WorkflowDefinition,
                WorkflowStep,
                WorkflowState,
                WorkflowStatus,
                StepResult,
                WorkflowResult,
            )
            return locals()[name]
        elif name in ["WorkflowGraph", "GraphValidator", "TopologicalSorter"]:
            from code_forge.workflows.graph import (
                WorkflowGraph,
                GraphValidator,
                TopologicalSorter,
            )
            return locals()[name]
        elif name in ["StateManager", "CheckpointManager", "StateManagementError", "CheckpointNotFoundError", "CheckpointCorruptedError"]:
            from code_forge.workflows.state import (
                StateManager,
                CheckpointManager,
                StateManagementError,
                CheckpointNotFoundError,
                CheckpointCorruptedError,
            )
            return locals()[name]
        elif name in ["WorkflowExecutor", "StepExecutor", "WorkflowExecutionError", "StepExecutionError"]:
            from code_forge.workflows.executor import (
                WorkflowExecutor,
                StepExecutor,
                WorkflowExecutionError,
                StepExecutionError,
            )
            return locals()[name]
        elif name == "WorkflowTemplateRegistry":
            from code_forge.workflows.registry import WorkflowTemplateRegistry
            return WorkflowTemplateRegistry
        elif name in ["YAMLWorkflowParser", "PythonWorkflowBuilder"]:
            from code_forge.workflows.parser import (
                YAMLWorkflowParser,
                PythonWorkflowBuilder,
            )
            return locals()[name]
        elif name in ["WorkflowCommand", "WorkflowListCommand", "WorkflowRunCommand", "WorkflowStatusCommand", "WorkflowResumeCommand", "WorkflowCancelCommand"]:
            from code_forge.workflows.commands import (
                WorkflowCommand,
                WorkflowListCommand,
                WorkflowRunCommand,
                WorkflowStatusCommand,
                WorkflowResumeCommand,
                WorkflowCancelCommand,
            )
            return locals()[name]
        elif name == "WorkflowTool":
            from code_forge.workflows.tool import WorkflowTool
            return WorkflowTool
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
