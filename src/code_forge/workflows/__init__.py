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
]

# Lazy imports to avoid circular dependencies
# Actual imports will be added as modules are implemented
