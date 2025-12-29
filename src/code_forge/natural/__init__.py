"""Natural language interpretation for Code-Forge.

This package provides conversational translation capabilities:
- Intent classification from natural language
- Parameter inference from context
- Tool sequence planning for complex requests
- Middleware for request preprocessing
"""

from .intent import Intent, IntentClassifier, IntentType
from .resolver import ParameterResolver, ResolvedParameters
from .planner import ToolSequencePlanner, PlannedStep
from .middleware import (
    NaturalLanguageMiddleware,
    ProcessedRequest,
    create_middleware,
)

__all__ = [
    "Intent",
    "IntentClassifier",
    "IntentType",
    "ParameterResolver",
    "ResolvedParameters",
    "ToolSequencePlanner",
    "PlannedStep",
    "NaturalLanguageMiddleware",
    "ProcessedRequest",
    "create_middleware",
]
