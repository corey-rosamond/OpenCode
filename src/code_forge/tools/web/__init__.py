"""Web tools for searching and fetching content.

This module provides WebSearchBaseTool and WebFetchBaseTool which
wrap the existing web functionality as BaseTool subclasses.
"""

from code_forge.tools.registry import ToolRegistry
from code_forge.tools.web.fetch import WebFetchBaseTool
from code_forge.tools.web.search import WebSearchBaseTool

__all__ = ["WebSearchBaseTool", "WebFetchBaseTool", "register_web_tools"]


def register_web_tools() -> None:
    """Register web tools with the registry."""
    registry = ToolRegistry()
    registry.register(WebSearchBaseTool())
    registry.register(WebFetchBaseTool())
