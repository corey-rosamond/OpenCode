"""
Built-in agent implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .communication import CommunicationAgent
from .configuration import ConfigurationAgent
from .debug import DebugAgent
from .dependency_analysis import DependencyAnalysisAgent
from .diagram import DiagramAgent
from .documentation import DocumentationAgent
from .explore import ExploreAgent
from .general import GeneralAgent
from .log_analysis import LogAnalysisAgent
from .migration_planning import MigrationPlanningAgent
from .performance_analysis import PerformanceAnalysisAgent
from .plan import PlanAgent
from .qa_manual import QAManualAgent
from .refactoring import RefactoringAgent
from .research import ResearchAgent
from .review import CodeReviewAgent
from .security_audit import SecurityAuditAgent
from .test_generation import TestGenerationAgent
from .tutorial import TutorialAgent
from .writing import WritingAgent

if TYPE_CHECKING:
    from ..base import Agent, AgentConfig, AgentContext
    pass


# Agent class registry
AGENT_CLASSES: dict[str, type[Agent]] = {
    # Original agents
    "explore": ExploreAgent,
    "plan": PlanAgent,
    "code-review": CodeReviewAgent,
    "general": GeneralAgent,
    # Coding agents
    "test-generation": TestGenerationAgent,
    "documentation": DocumentationAgent,
    "refactoring": RefactoringAgent,
    "debug": DebugAgent,
    # Writing & Communication agents
    "writing": WritingAgent,
    "communication": CommunicationAgent,
    "tutorial": TutorialAgent,
    # Visual & Design agents
    "diagram": DiagramAgent,
    # Testing & QA agents
    "qa-manual": QAManualAgent,
    # Research & Analysis agents
    "research": ResearchAgent,
    "log-analysis": LogAnalysisAgent,
    "performance-analysis": PerformanceAnalysisAgent,
    # Security & Dependencies agents
    "security-audit": SecurityAuditAgent,
    "dependency-analysis": DependencyAnalysisAgent,
    # Project Management agents
    "migration-planning": MigrationPlanningAgent,
    "configuration": ConfigurationAgent,
}


def create_agent(
    agent_type: str,
    task: str,
    config: AgentConfig,
    context: AgentContext | None = None,
) -> Agent:
    """Create an agent of the specified type.

    Args:
        agent_type: Type identifier.
        task: Task description.
        config: Agent configuration.
        context: Execution context.

    Returns:
        Agent instance.
    """
    agent_class = AGENT_CLASSES.get(agent_type)

    if agent_class is None:
        # Fall back to general agent for unknown types
        agent_class = GeneralAgent

    return agent_class(task=task, config=config, context=context)


def register_agent_class(name: str, agent_class: type[Agent]) -> None:
    """Register a custom agent class.

    Args:
        name: Type identifier.
        agent_class: Agent class to register.
    """
    AGENT_CLASSES[name] = agent_class


def unregister_agent_class(name: str) -> bool:
    """Unregister a custom agent class.

    Args:
        name: Type identifier.

    Returns:
        True if removed, False if not found.
    """
    if name in AGENT_CLASSES:
        del AGENT_CLASSES[name]
        return True
    return False


def list_agent_classes() -> list[str]:
    """List registered agent class names.

    Returns:
        List of agent type names.
    """
    return list(AGENT_CLASSES.keys())


__all__ = [
    "AGENT_CLASSES",
    "CodeReviewAgent",
    "CommunicationAgent",
    "ConfigurationAgent",
    "DebugAgent",
    "DependencyAnalysisAgent",
    "DiagramAgent",
    "DocumentationAgent",
    "ExploreAgent",
    "GeneralAgent",
    "LogAnalysisAgent",
    "MigrationPlanningAgent",
    "PerformanceAnalysisAgent",
    "PlanAgent",
    "QAManualAgent",
    "RefactoringAgent",
    "ResearchAgent",
    "SecurityAuditAgent",
    "TestGenerationAgent",
    "TutorialAgent",
    "WritingAgent",
    "create_agent",
    "list_agent_classes",
    "register_agent_class",
    "unregister_agent_class",
]
