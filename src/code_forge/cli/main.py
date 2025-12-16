"""CLI entry point for Code-Forge."""

from __future__ import annotations

import asyncio
import os
import re
import sys
from typing import TYPE_CHECKING

from code_forge import __version__
from code_forge.cli.repl import CodeForgeREPL
from code_forge.config import ConfigLoader
from code_forge.core import get_logger

if TYPE_CHECKING:
    from code_forge.config import CodeForgeConfig

logger = get_logger("cli")

# Pattern to match keyboard escape sequences that may bleed into output
# during streaming (e.g., ^[[6~ for Page Down, ^[[5~ for Page Up, etc.)
KEYBOARD_ESCAPE_PATTERN = re.compile(
    r'\x1b\['           # ESC [
    r'[0-9;]*'          # Optional numeric parameters
    r'[~A-Za-z]'        # Terminator character
)


def strip_keyboard_escapes(text: str) -> str:
    """Remove keyboard escape sequences from text.

    During streaming output, keyboard input can sometimes bleed into
    the output stream. This strips those escape sequences.

    Args:
        text: Text that may contain escape sequences

    Returns:
        Text with keyboard escape sequences removed
    """
    return KEYBOARD_ESCAPE_PATTERN.sub('', text)


def main() -> int:
    """Main entry point for Code-Forge CLI.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = sys.argv[1:]

    if "--version" in args or "-v" in args:
        print(f"forge {__version__}")
        return 0

    if "--help" in args or "-h" in args:
        print_help()
        return 0

    # Check for unknown flags
    for arg in args:
        if arg.startswith("-") and arg not in (
            "-v",
            "--version",
            "-h",
            "--help",
            "-p",
            "--print",
            "--continue",
            "--resume",
        ):
            print(f"Error: Unknown option '{arg}'", file=sys.stderr)
            print("Run 'forge --help' for usage information", file=sys.stderr)
            return 1

    # Load configuration
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_all()
    except Exception as e:
        logger.exception("Failed to load configuration")
        print(f"Error: Failed to load configuration: {e}", file=sys.stderr)
        return 1

    # Check for API key - run setup wizard if not configured
    api_key = os.environ.get("OPENROUTER_API_KEY") or config.get_api_key()
    if not api_key:
        from code_forge.cli.setup import run_setup_wizard
        api_key = run_setup_wizard()
        if not api_key:
            return 1  # User cancelled setup

    # Start REPL
    try:
        repl = CodeForgeREPL(config)
        return asyncio.run(run_with_agent(repl, config, api_key))
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.exception("REPL error")
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def run_with_agent(repl: CodeForgeREPL, config: CodeForgeConfig, api_key: str) -> int:
    """Run REPL with agent and command handling.

    Args:
        repl: The REPL instance.
        config: Application configuration.
        api_key: OpenRouter API key.

    Returns:
        Exit code.
    """
    from code_forge.commands import CommandExecutor, CommandContext, register_builtin_commands
    from code_forge.langchain.llm import OpenRouterLLM
    from code_forge.langchain.agent import CodeForgeAgent
    from code_forge.langchain.tools import adapt_tools_for_langchain
    from code_forge.llm import OpenRouterClient
    from code_forge.tools import ToolRegistry, register_all_tools
    from code_forge.sessions import SessionManager
    from code_forge.modes import ModeManager, ModeName, ModeContext, setup_modes

    # Register tools
    register_all_tools()
    tool_registry = ToolRegistry()

    # Create OpenRouter client and LLM
    from code_forge.llm.routing import get_model_context_limit

    client = OpenRouterClient(api_key=api_key)
    llm = OpenRouterLLM(
        client=client,
        model=config.model.default,
    )

    # Update status bar with model info
    model_context = get_model_context_limit(config.model.default)
    repl._status.set_model(config.model.default)
    repl._status.set_tokens(0, model_context)

    # Create agent with tools (wrapped for LangChain compatibility)
    raw_tools = [tool_registry.get(name) for name in tool_registry.list_names()]
    raw_tools = [t for t in raw_tools if t is not None]
    tools = adapt_tools_for_langchain(raw_tools)
    agent = CodeForgeAgent(
        llm=llm,
        tools=tools,
    )

    # Set up mode manager with thinking mode
    mode_manager = setup_modes()

    # Create mode context for mode switching
    def mode_output(msg: str) -> None:
        repl.output.print_dim(msg)

    mode_context = ModeContext(output=mode_output)

    # Set system prompt to instruct the LLM to use tools
    from code_forge.llm.models import Message
    from code_forge.langchain.prompts import get_system_prompt

    tool_names = [t.name for t in tools if t is not None and hasattr(t, "name")]
    base_system_prompt = get_system_prompt(
        tool_names=tool_names,
        working_directory=os.getcwd(),
        model=config.model.default,
    )

    # Function to update system prompt based on current mode
    def update_system_prompt() -> None:
        """Update system prompt with current mode's modifications."""
        modified_prompt = mode_manager.get_system_prompt(base_system_prompt)
        agent.memory.set_system_message(Message.system(modified_prompt))

    update_system_prompt()

    # Connect thinking toggle to mode manager
    original_toggle = repl._toggle_thinking

    def thinking_toggle_with_mode() -> None:
        """Toggle thinking mode in both UI and mode manager."""
        original_toggle()
        # Switch mode based on new state
        if repl.thinking_enabled:
            mode_manager.switch_mode(ModeName.THINKING, mode_context)
            repl._status.set_mode("Thinking")
        else:
            mode_manager.switch_mode(ModeName.NORMAL, mode_context)
            repl._status.set_mode("Normal")
        # Update the system prompt
        update_system_prompt()

    # Replace the toggle function
    repl._toggle_thinking = thinking_toggle_with_mode

    # Create session manager
    session_manager = SessionManager.get_instance()
    session = session_manager.create(title="CLI Session")

    # Register commands
    register_builtin_commands()

    # Create command context
    command_context = CommandContext(
        session_manager=session_manager,
        config=config,
        llm=llm,
    )

    # Create command executor (uses default registry and parser)
    command_executor = CommandExecutor()

    # Track cumulative token usage (use list for mutable closure)
    total_tokens = [0]

    # Register input handler
    async def handle_input(text: str) -> None:
        """Handle user input - route to commands or agent."""
        if text.startswith("/"):
            # Execute command
            cmd_result = await command_executor.execute(text, command_context)
            if cmd_result.output:
                repl.output.print(cmd_result.output)
            if cmd_result.error:
                repl.output.print_error(cmd_result.error)

            # Check for exit command
            if text.strip() in ("/exit", "/quit", "/q"):
                repl.stop()
        else:
            # Send to agent with streaming
            from code_forge.langchain.agent import AgentEventType
            from rich.status import Status

            repl._status.set_status("Thinking...")

            # Initialize spinners before try block to avoid NameError in except/finally
            spinner = None
            tool_spinner = None

            try:
                # Add user message to session
                session_manager.add_message("user", text)

                # Stream agent execution with real-time output
                accumulated_output = ""
                current_tool = None
                iteration_count = 0
                first_content_received = False

                repl.output.print("")  # Start on new line

                # Start with a spinner until we get content
                spinner = Status("[dim]Thinking...[/dim]", console=repl._console, spinner="dots")
                spinner.start()

                async for event in agent.stream(text):
                    if event.type == AgentEventType.LLM_START:
                        iteration_count = event.data.get("iteration", 0)
                        if iteration_count > 1:
                            repl._status.set_status(f"Thinking (iteration {iteration_count})...")

                    elif event.type == AgentEventType.LLM_CHUNK:
                        # Stream text output in real-time
                        chunk = event.data.get("content", "")
                        if chunk:
                            # Filter out keyboard escape sequences that may bleed in
                            chunk = strip_keyboard_escapes(chunk)
                            if chunk:  # Only proceed if content remains after filtering
                                # Stop spinner on first content
                                if not first_content_received:
                                    spinner.stop()
                                    first_content_received = True
                                repl._console.print(chunk, end="")
                                accumulated_output += chunk

                    elif event.type == AgentEventType.LLM_END:
                        pass  # Content already streamed

                    elif event.type == AgentEventType.TOOL_START:
                        # Stop thinking spinner if still running
                        if not first_content_received:
                            spinner.stop()
                            first_content_received = True

                        tool_name = event.data.get("name", "unknown")
                        tool_args = event.data.get("arguments", {})
                        current_tool = tool_name

                        # Show tool call with formatted arguments
                        repl.output.print("")  # New line before tool
                        args_display = _format_tool_args(tool_args)
                        repl._console.print(
                            f"[dim]─── Tool: [bold cyan]{tool_name}[/bold cyan]{args_display} ───[/dim]"
                        )
                        repl._status.set_status(f"Running {tool_name}...")

                        # Start a tool execution spinner
                        tool_spinner = Status(
                            f"[dim]⏳ Running {tool_name}...[/dim]",
                            console=repl._console,
                            spinner="dots"
                        )
                        tool_spinner.start()

                    elif event.type == AgentEventType.TOOL_END:
                        # Stop tool spinner
                        if tool_spinner:
                            tool_spinner.stop()
                            tool_spinner = None

                        tool_name = event.data.get("name", "unknown")
                        result = event.data.get("result", "")
                        success = event.data.get("success", True)
                        duration = event.data.get("duration", 0)

                        # Show truncated result
                        result_preview = _truncate_result(result, max_lines=5)
                        status = "[green]✓[/green]" if success else "[red]✗[/red]"
                        repl._console.print(f"[dim]{result_preview}[/dim]")
                        repl._console.print(
                            f"[dim]─── {status} {tool_name} ({duration:.1f}s) ───[/dim]"
                        )
                        repl.output.print("")  # Blank line after tool
                        current_tool = None
                        repl._status.set_status("Thinking...")

                    elif event.type == AgentEventType.AGENT_END:
                        iterations = event.data.get("iterations", 0)
                        tool_count = event.data.get("tool_calls", 0)
                        duration = event.data.get("duration", 0)
                        prompt_tokens = event.data.get("prompt_tokens", 0)
                        completion_tokens = event.data.get("completion_tokens", 0)
                        event_total_tokens = event.data.get("total_tokens", 0)

                        # Update cumulative token count and status bar
                        total_tokens[0] += event_total_tokens
                        repl._status.set_tokens(total_tokens[0])

                        # Final stats (optional, can be dimmed)
                        if tool_count > 0 or event_total_tokens > 0:
                            token_info = ""
                            if event_total_tokens > 0:
                                token_info = f", {event_total_tokens:,} tokens"
                            repl._console.print(
                                f"\n[dim]Completed in {duration:.1f}s "
                                f"({iterations} iteration{'s' if iterations != 1 else ''}, "
                                f"{tool_count} tool call{'s' if tool_count != 1 else ''}"
                                f"{token_info})[/dim]"
                            )

                    elif event.type == AgentEventType.ERROR:
                        error = event.data.get("error", "Unknown error")
                        repl.output.print_error(f"Agent error: {error}")

                repl.output.print("")  # Final newline

                # Process response through mode manager (extracts thinking if in thinking mode)
                processed_output = mode_manager.process_response(accumulated_output)

                # Add assistant message to session
                session_manager.add_message("assistant", processed_output)

            except Exception as e:
                logger.exception("Agent error")
                # Stop spinners if still running
                if spinner and not first_content_received:
                    spinner.stop()
                if tool_spinner:
                    tool_spinner.stop()
                repl.output.print_error(f"Error: {e}")
            finally:
                # Ensure all spinners are stopped
                if spinner:
                    try:
                        spinner.stop()
                    except Exception:
                        pass
                if tool_spinner:
                    try:
                        tool_spinner.stop()
                    except Exception:
                        pass
                repl._status.set_status("Ready")

    repl.on_input(handle_input)

    # Run REPL
    return await repl.run()


def _format_tool_args(args: dict) -> str:
    """Format tool arguments for display.

    Args:
        args: Tool arguments dictionary.

    Returns:
        Formatted string of key arguments.
    """
    if not args:
        return ""

    # Show key arguments inline
    parts = []
    for key, value in args.items():
        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 50:
                value = value[:47] + "..."
            # Show file paths and short strings
            if "/" in value or len(value) < 30:
                parts.append(f"{key}={value}")
        elif isinstance(value, (int, float, bool)):
            parts.append(f"{key}={value}")

    if parts:
        return " (" + ", ".join(parts[:3]) + ")"  # Limit to 3 args
    return ""


def _truncate_result(result: str, max_lines: int = 5) -> str:
    """Truncate tool result for display.

    Args:
        result: Tool result string.
        max_lines: Maximum lines to show.

    Returns:
        Truncated result string.
    """
    if not result:
        return "(no output)"

    lines = result.split("\n")
    if len(lines) <= max_lines:
        return result

    shown = lines[:max_lines]
    remaining = len(lines) - max_lines
    return "\n".join(shown) + f"\n... ({remaining} more lines)"


def print_help() -> None:
    """Print help message."""
    help_text = """
Code-Forge - AI-powered CLI Development Assistant

Usage: forge [OPTIONS] [PROMPT]

Options:
  -v, --version     Show version and exit
  -h, --help        Show this help message
  --continue        Resume most recent session
  --resume          Select session to resume
  -p, --print       Run in headless mode with prompt

For more information, visit: https://github.com/corey-rosamond/Code-Forge
"""
    print(help_text.strip())


if __name__ == "__main__":
    sys.exit(main())
