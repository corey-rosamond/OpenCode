"""User confirmation prompts for permission requests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from code_forge.permissions.models import PermissionLevel, PermissionRule


class ConfirmationChoice(str, Enum):
    """User choices for permission confirmation."""

    ALLOW = "allow"
    ALLOW_ALWAYS = "allow_always"
    DENY = "deny"
    DENY_ALWAYS = "deny_always"
    TIMEOUT = "timeout"


@dataclass
class ConfirmationRequest:
    """
    Request for user confirmation.

    Attributes:
        tool_name: Name of the tool requesting permission
        arguments: Tool arguments
        description: Description of what the tool will do
        timeout: Timeout in seconds (0 = no timeout)
    """

    tool_name: str
    arguments: dict[str, Any]
    description: str = ""
    timeout: float = 30.0


class PermissionPrompt:
    """
    Handles user confirmation prompts.

    This is an abstract base that can be implemented for different
    UI contexts (terminal, GUI, etc.).
    """

    def __init__(
        self,
        input_handler: Callable[[str], str] | None = None,
        output_handler: Callable[[str], None] | None = None,
    ) -> None:
        """
        Initialize prompt handler.

        Args:
            input_handler: Function to get user input
            output_handler: Function to display output
        """
        self.input_handler = input_handler or input
        self.output_handler = output_handler or print

    def format_request(self, request: ConfirmationRequest) -> str:
        """
        Format a confirmation request for display.

        Args:
            request: The confirmation request

        Returns:
            Formatted string for display
        """
        width = 62
        lines = [
            "\u250c" + "\u2500" * width + "\u2510",
            "\u2502  Permission Required" + " " * (width - 21) + "\u2502",
            "\u251c" + "\u2500" * width + "\u2524",
        ]

        # Tool name line
        tool_line = f"  Tool: {request.tool_name}"
        lines.append(f"\u2502{tool_line:<{width}}\u2502")

        # Format arguments
        for key, value in request.arguments.items():
            value_str = str(value)
            if len(value_str) > 45:
                value_str = value_str[:42] + "..."
            arg_line = f"  {key}: {value_str}"
            if len(arg_line) > width:
                arg_line = arg_line[: width - 3] + "..."
            lines.append(f"\u2502{arg_line:<{width}}\u2502")

        # Add description if present
        if request.description:
            lines.append("\u2502" + " " * width + "\u2502")
            desc = request.description
            if len(desc) > width - 4:
                desc = desc[: width - 7] + "..."
            desc_line = f"  {desc}"
            lines.append(f"\u2502{desc_line:<{width}}\u2502")

        lines.extend(
            [
                "\u2502" + " " * width + "\u2502",
                "\u2502  [a] Allow    [A] Allow Always    "
                "[d] Deny    [D] Deny Always\u2502",
                "\u2514" + "\u2500" * width + "\u2518",
            ]
        )

        return "\n".join(lines)

    def confirm(self, request: ConfirmationRequest) -> ConfirmationChoice:
        """
        Prompt user for confirmation (synchronous).

        Note: This method does NOT support timeouts. The `request.timeout`
        parameter is ignored. Use `confirm_async()` for timeout support.

        Args:
            request: The confirmation request (timeout is ignored)

        Returns:
            User's choice
        """
        self.output_handler(self.format_request(request))
        self.output_handler("")

        try:
            response = self.input_handler("Choice [a/A/d/D]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return ConfirmationChoice.DENY

        return self._parse_response(response)

    async def confirm_async(
        self, request: ConfirmationRequest
    ) -> ConfirmationChoice:
        """
        Prompt user for confirmation (asynchronous with timeout).

        Args:
            request: The confirmation request

        Returns:
            User's choice, or TIMEOUT if timed out
        """
        self.output_handler(self.format_request(request))
        self.output_handler("")

        if request.timeout > 0:
            try:
                # Run input in executor with timeout
                loop = asyncio.get_running_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.input_handler("Choice [a/A/d/D]: ").strip(),
                    ),
                    timeout=request.timeout,
                )
                return self._parse_response(response)
            except TimeoutError:
                self.output_handler("\nTimeout - permission denied.")
                return ConfirmationChoice.TIMEOUT
            except (EOFError, KeyboardInterrupt):
                return ConfirmationChoice.DENY
        else:
            # No timeout
            return self.confirm(request)

    def _parse_response(self, response: str) -> ConfirmationChoice:
        """Parse user response into choice."""
        if response == "a":
            return ConfirmationChoice.ALLOW
        elif response == "A":
            return ConfirmationChoice.ALLOW_ALWAYS
        elif response in ("d", ""):  # Default to deny
            return ConfirmationChoice.DENY
        elif response == "D":
            return ConfirmationChoice.DENY_ALWAYS
        else:
            # Invalid input defaults to deny
            return ConfirmationChoice.DENY


def create_rule_from_choice(
    choice: ConfirmationChoice,
    tool_name: str,
    arguments: dict[str, Any],  # noqa: ARG001
) -> PermissionRule | None:
    """
    Create a permission rule from a confirmation choice.

    Only creates rules for "always" choices.

    Args:
        choice: The user's choice
        tool_name: Name of the tool
        arguments: Tool arguments (reserved for future pattern expansion)

    Returns:
        PermissionRule if an "always" choice, else None
    """
    if choice == ConfirmationChoice.ALLOW_ALWAYS:
        # Create allow rule for this tool
        pattern = f"tool:{tool_name}"
        return PermissionRule(
            pattern=pattern,
            permission=PermissionLevel.ALLOW,
            description=f"User allowed: {tool_name}",
            priority=100,
        )

    elif choice == ConfirmationChoice.DENY_ALWAYS:
        # Create deny rule for this tool
        pattern = f"tool:{tool_name}"
        return PermissionRule(
            pattern=pattern,
            permission=PermissionLevel.DENY,
            description=f"User denied: {tool_name}",
            priority=100,
        )

    return None
