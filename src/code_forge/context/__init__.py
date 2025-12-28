"""Context management package.

This package provides context window management for Code-Forge,
including token counting, truncation strategies, and compaction.

Example:
    from code_forge.context import ContextManager, TruncationMode

    # Create manager for model
    manager = ContextManager(
        model="anthropic/claude-3-opus",
        mode=TruncationMode.SMART,
    )

    # Set system prompt
    manager.set_system_prompt("You are a helpful assistant.")

    # Add messages
    manager.add_message({"role": "user", "content": "Hello"})
    manager.add_message({"role": "assistant", "content": "Hi there!"})

    # Check usage
    print(f"Usage: {manager.usage_percentage:.1f}%")

    # Get messages for request
    messages = manager.get_context_for_request()
"""

from .compaction import ContextCompactor, ToolResultCompactor
from .events import (
    CompressionEvent,
    CompressionEventType,
    CompressionObserver,
    WarningLevel,
    get_warning_level,
)
from .limits import ContextBudget, ContextLimits, ContextTracker
from .manager import ContextManager, TruncationMode, get_strategy
from .strategies import (
    CompositeStrategy,
    SelectiveTruncationStrategy,
    SlidingWindowStrategy,
    SmartTruncationStrategy,
    TokenBudgetStrategy,
    TruncationStrategy,
)
from .tokens import (
    ApproximateCounter,
    CachingCounter,
    TiktokenCounter,
    TokenCounter,
    get_counter,
)
from .profiles import (
    LanguageProfile,
    generate_project_context,
    get_profile,
    get_profile_for_project,
)
from .project_detector import (
    ProjectInfo,
    ProjectType,
    ProjectTypeDetector,
    detect_project,
    get_detector,
)

__all__ = [
    "ApproximateCounter",
    "CachingCounter",
    "CompositeStrategy",
    "CompressionEvent",
    "CompressionEventType",
    "CompressionObserver",
    "ContextBudget",
    "ContextCompactor",
    "ContextLimits",
    "ContextManager",
    "ContextTracker",
    "LanguageProfile",
    "ProjectInfo",
    "ProjectType",
    "ProjectTypeDetector",
    "SelectiveTruncationStrategy",
    "SlidingWindowStrategy",
    "SmartTruncationStrategy",
    "TiktokenCounter",
    "TokenBudgetStrategy",
    "TokenCounter",
    "ToolResultCompactor",
    "TruncationMode",
    "TruncationStrategy",
    "WarningLevel",
    "detect_project",
    "generate_project_context",
    "get_counter",
    "get_detector",
    "get_profile",
    "get_profile_for_project",
    "get_strategy",
    "get_warning_level",
]
