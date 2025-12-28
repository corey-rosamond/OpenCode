# Plugin Development Guide

This guide explains how to create plugins for Code-Forge.

## Plugin Structure

A plugin consists of:

```
my-plugin/
├── plugin.yaml      # Manifest file
├── __init__.py      # Package init
└── my_plugin.py     # Plugin implementation
```

## Manifest File

The `plugin.yaml` manifest defines your plugin:

```yaml
name: my-plugin
version: 1.0.0
description: A sample plugin
author: Your Name
homepage: https://github.com/you/my-plugin

# Entry point: module:ClassName
entry_point: my_plugin:MyPlugin

# What capabilities this plugin provides
capabilities:
  tools: true
  commands: true
  hooks: false
  subagents: false
  skills: false

# Python dependencies (optional)
dependencies:
  - requests>=2.28.0

# Code-Forge version compatibility
forge_version: ">=1.0.0"

# Plugin-specific configuration schema (optional)
config_schema:
  api_key:
    type: string
    description: API key for the service
    required: false
```

## Plugin Implementation

Create a class that extends `Plugin`:

```python
"""My plugin implementation."""

from code_forge.plugins import Plugin, PluginMetadata, PluginCapabilities, PluginContext
from code_forge.tools import BaseTool, ToolParameter, ToolResult, ToolCategory


class MyTool(BaseTool):
    """Custom tool provided by the plugin."""

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.UTILITY

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Input value",
                required=True,
            )
        ]

    async def execute(self, **kwargs) -> ToolResult:
        input_val = kwargs.get("input", "")
        # Do something with input
        return ToolResult(
            success=True,
            output=f"Processed: {input_val}",
        )


class MyPlugin(Plugin):
    """Main plugin class."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="A sample plugin",
            author="Your Name",
        )

    @property
    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(
            tools=True,
            commands=False,
            hooks=False,
        )

    def activate(self, context: PluginContext) -> None:
        """Called when plugin is activated."""
        self.context = context
        # Initialize resources

    def deactivate(self) -> None:
        """Called when plugin is deactivated."""
        # Cleanup resources

    def register_tools(self) -> list[BaseTool]:
        """Return tools to register."""
        return [MyTool()]
```

## Plugin Capabilities

### Tools

Provide custom tools:

```python
def register_tools(self) -> list[BaseTool]:
    return [MyTool1(), MyTool2()]
```

### Commands

Provide slash commands:

```python
from code_forge.commands import Command, CommandResult

class MyCommand(Command):
    @property
    def name(self) -> str:
        return "mycommand"

    async def execute(self, **kwargs) -> CommandResult:
        return CommandResult(success=True, output="Done!")

def register_commands(self) -> list[Command]:
    return [MyCommand()]
```

### Hooks

Register event hooks:

```python
from code_forge.hooks import Hook

def register_hooks(self) -> list[Hook]:
    return [
        Hook(
            event_pattern="tool:post_execute",
            callback=self.on_tool_complete,
        )
    ]

async def on_tool_complete(self, event):
    # Handle event
    pass
```

## Plugin Context

The `PluginContext` provides:

```python
def activate(self, context: PluginContext) -> None:
    # Plugin ID
    plugin_id = context.plugin_id

    # Data directory for persistence
    data_dir = context.data_dir

    # Plugin configuration
    config = context.config

    # Logger instance
    logger = context.logger
```

## Installation

Install plugins in:
- User directory: `~/.forge/plugins/my-plugin/`
- Project directory: `.forge/plugins/my-plugin/`

Or install via pip if published as a package.

## Best Practices

1. **Use async** - All tool execution should be async
2. **Handle errors** - Return ToolResult with success=False on errors
3. **Document** - Provide clear descriptions for tools
4. **Validate** - Check inputs before processing
5. **Cleanup** - Release resources in deactivate()
6. **Test** - Write tests for your plugin
