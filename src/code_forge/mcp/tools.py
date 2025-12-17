"""Adapter for MCP tools to Code-Forge tool interface."""

from __future__ import annotations

import logging
import re
from typing import Any

from code_forge.mcp.client import MCPClient
from code_forge.mcp.protocol import MCPTool

logger = logging.getLogger(__name__)


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use as an identifier.

    Replaces invalid characters with underscores.

    Args:
        name: The name to sanitize.

    Returns:
        The sanitized name.
    """
    # Replace common separators with underscores
    result = re.sub(r"[-./]", "_", name)
    # Remove any other non-alphanumeric characters
    result = re.sub(r"[^a-zA-Z0-9_]", "", result)
    # Ensure doesn't start with a number
    if result and result[0].isdigit():
        result = "_" + result
    return result


class MCPToolAdapter:
    """Adapts MCP tools to Code-Forge Tool interface."""

    def __init__(self, client: MCPClient, server_name: str) -> None:
        """Initialize adapter.

        Args:
            client: MCP client.
            server_name: Server name for namespacing.
        """
        self.client = client
        self.server_name = server_name
        self._sanitized_server = _sanitize_name(server_name)

    def get_tool_name(self, mcp_tool: MCPTool) -> str:
        """Get namespaced tool name.

        Format: mcp__{server}__{tool}

        Args:
            mcp_tool: The MCP tool.

        Returns:
            The namespaced tool name.
        """
        tool = _sanitize_name(mcp_tool.name)
        return f"mcp__{self._sanitized_server}__{tool}"

    def get_original_tool_name(self, namespaced_name: str) -> str | None:
        """Get the original tool name from a namespaced name.

        Args:
            namespaced_name: The namespaced tool name.

        Returns:
            The original tool name, or None if not from this adapter.
        """
        prefix = f"mcp__{self._sanitized_server}__"
        if namespaced_name.startswith(prefix):
            return namespaced_name[len(prefix) :]
        return None

    def create_tool_definition(self, mcp_tool: MCPTool) -> dict[str, Any]:
        """Create tool definition for LangChain.

        Args:
            mcp_tool: MCP tool definition.

        Returns:
            Tool definition dict.
        """
        return {
            "name": self.get_tool_name(mcp_tool),
            "description": mcp_tool.description,
            "parameters": mcp_tool.input_schema,
            "mcp_server": self.server_name,
            "mcp_tool": mcp_tool.name,
        }

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Execute MCP tool.

        Args:
            tool_name: Namespaced tool name.
            arguments: Tool arguments.

        Returns:
            Tool result as a string.

        Raises:
            ValueError: If tool name is invalid.
        """
        # Extract original tool name
        # Format: mcp__<server>__<tool_name>
        parts = tool_name.split("__")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid MCP tool name format: {tool_name}. "
                f"Expected 'mcp__<server>__<tool>', got {len(parts)} parts"
            )
        if parts[0] != "mcp":
            raise ValueError(
                f"Invalid MCP tool name prefix: {tool_name}. "
                f"Expected 'mcp__', got '{parts[0]}__'"
            )
        if not parts[1]:
            raise ValueError(f"Invalid MCP tool name: empty server name in {tool_name}")
        if not parts[2]:
            raise ValueError(f"Invalid MCP tool name: empty tool name in {tool_name}")

        # The original name might have underscores replaced
        # We stored the mapping, so use the original
        original_name = parts[2]

        logger.info(f"Executing MCP tool: {original_name} on server {self.server_name}")
        result = await self.client.call_tool(original_name, arguments)

        # Process result content
        return self._format_result(result)

    def _format_result(self, result: list[dict[str, Any]]) -> str:
        """Format tool result content as a string.

        Args:
            result: The tool result content list.

        Returns:
            Formatted string result.
        """
        if not result:
            return ""

        texts: list[str] = []
        for item in result:
            if isinstance(item, dict):
                item_type = item.get("type", "text")
                if item_type == "text":
                    texts.append(item.get("text", ""))
                elif item_type == "image":
                    mime = item.get("mimeType", "image")
                    texts.append(f"[Image: {mime}]")
                elif item_type == "resource":
                    uri = item.get("uri", "")
                    texts.append(f"[Resource: {uri}]")
                # Unknown type, try to extract text
                elif "text" in item:
                    texts.append(item["text"])
                else:
                    texts.append(str(item))
            else:
                texts.append(str(item))

        return "\n".join(texts)


class MCPToolRegistry:
    """Registry for MCP tools from all connected servers."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._tools: dict[str, dict[str, Any]] = {}
        self._adapters: dict[str, MCPToolAdapter] = {}
        self._tool_to_original: dict[str, str] = {}

    def register_server_tools(
        self,
        adapter: MCPToolAdapter,
        tools: list[MCPTool],
    ) -> list[str]:
        """Register tools from a server.

        Args:
            adapter: Tool adapter for the server.
            tools: List of MCP tools.

        Returns:
            List of registered tool names.
        """
        registered: list[str] = []
        for tool in tools:
            name = adapter.get_tool_name(tool)
            self._tools[name] = adapter.create_tool_definition(tool)
            self._adapters[name] = adapter
            self._tool_to_original[name] = tool.name
            registered.append(name)
            logger.info(f"Registered MCP tool: {name}")
        return registered

    def unregister_server_tools(self, server_name: str) -> list[str]:
        """Unregister all tools from a server.

        Args:
            server_name: Server name.

        Returns:
            List of unregistered tool names.
        """
        prefix = f"mcp__{_sanitize_name(server_name)}__"
        unregistered: list[str] = []

        for name in list(self._tools.keys()):
            if name.startswith(prefix):
                del self._tools[name]
                del self._adapters[name]
                self._tool_to_original.pop(name, None)
                unregistered.append(name)
                logger.info(f"Unregistered MCP tool: {name}")

        return unregistered

    def get_tool(self, name: str) -> dict[str, Any] | None:
        """Get tool definition by name.

        Args:
            name: Tool name.

        Returns:
            Tool definition or None if not found.
        """
        return self._tools.get(name)

    def get_adapter(self, name: str) -> MCPToolAdapter | None:
        """Get adapter for tool.

        Args:
            name: Tool name.

        Returns:
            Tool adapter or None if not found.
        """
        return self._adapters.get(name)

    def get_original_name(self, name: str) -> str | None:
        """Get original tool name.

        Args:
            name: Namespaced tool name.

        Returns:
            Original tool name or None if not found.
        """
        return self._tool_to_original.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.

        Returns:
            List of tool definitions.
        """
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        """Check if tool exists.

        Args:
            name: Tool name.

        Returns:
            True if tool exists, False otherwise.
        """
        return name in self._tools

    def is_mcp_tool(self, name: str) -> bool:
        """Check if a tool name is an MCP tool.

        Args:
            name: Tool name.

        Returns:
            True if it's an MCP tool format.
        """
        return name.startswith("mcp__")

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result.

        Raises:
            ValueError: If tool not found.
        """
        adapter = self._adapters.get(name)
        if adapter is None:
            raise ValueError(f"Unknown MCP tool: {name}")

        # Get original name for the call
        original_name = self._tool_to_original.get(name)
        if original_name is None:
            raise ValueError(f"Original name not found for: {name}")

        # Execute through the client directly with original name
        logger.info(f"Executing MCP tool: {original_name}")
        result = await adapter.client.call_tool(original_name, arguments)
        return adapter._format_result(result)

    def get_tools_for_server(self, server_name: str) -> list[dict[str, Any]]:
        """Get all tools for a specific server.

        Args:
            server_name: Server name.

        Returns:
            List of tool definitions for that server.
        """
        prefix = f"mcp__{_sanitize_name(server_name)}__"
        return [
            tool for name, tool in self._tools.items() if name.startswith(prefix)
        ]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._adapters.clear()
        self._tool_to_original.clear()
