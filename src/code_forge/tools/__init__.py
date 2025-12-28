"""Tools package for Code-Forge.

This package provides the tool system foundation:
- BaseTool: Abstract base class for all tools (Command pattern)
- ToolRegistry: Singleton registry for tool management
- ToolExecutor: Tool execution with tracking and schema generation

Models:
- ToolParameter: Tool parameter definition with JSON Schema generation
- ToolResult: Tool execution result
- ExecutionContext: Execution context (working dir, timeout, etc.)
- ToolExecution: Record of a tool execution
- ToolCategory: Enum for categorizing tools

Usage:
    from code_forge.tools import (
        BaseTool,
        ToolParameter,
        ToolResult,
        ExecutionContext,
        ToolCategory,
        ToolRegistry,
        ToolExecutor,
    )

    class MyTool(BaseTool):
        @property
        def name(self) -> str:
            return "MyTool"
        # ... implement other abstract properties and methods

    registry = ToolRegistry()
    registry.register(MyTool())
    executor = ToolExecutor(registry)
    result = await executor.execute("MyTool", context, param="value")
"""

from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolExecution,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.execution import (
    BashOutputTool,
    BashTool,
    KillShellTool,
    ShellManager,
    ShellProcess,
    ShellStatus,
    register_execution_tools,
)
from code_forge.tools.executor import ToolExecutor
from code_forge.tools.file import (
    EditTool,
    GlobTool,
    GrepTool,
    ReadTool,
    WriteTool,
    register_file_tools,
)
from code_forge.tools.registry import ToolRegistry
from code_forge.tools.task import TaskTool, register_task_tools
from code_forge.tools.web import (
    WebFetchBaseTool,
    WebSearchBaseTool,
    register_web_tools,
)

__all__ = [
    "BaseTool",
    "BashOutputTool",
    "BashTool",
    "EditTool",
    "ExecutionContext",
    "GlobTool",
    "GrepTool",
    "KillShellTool",
    "ReadTool",
    "ShellManager",
    "ShellProcess",
    "ShellStatus",
    "TaskTool",
    "ToolCategory",
    "ToolExecution",
    "ToolExecutor",
    "ToolParameter",
    "ToolRegistry",
    "ToolResult",
    "WebFetchBaseTool",
    "WebSearchBaseTool",
    "WriteTool",
    "register_all_tools",
    "register_execution_tools",
    "register_file_tools",
    "register_task_tools",
    "register_web_tools",
]


def register_all_tools() -> None:
    """Register all built-in tools with the registry."""
    register_file_tools()
    register_execution_tools()
    register_task_tools()
    register_web_tools()
