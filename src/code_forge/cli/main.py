"""CLI entry point for Code-Forge."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from typing import TYPE_CHECKING

from code_forge import __version__
from code_forge.cli.conversation import ErrorExplainer
from code_forge.cli.dependencies import Dependencies
from code_forge.cli.interrupt import get_interrupt_handler
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

    # Parse output format flags
    no_color = "--no-color" in args
    quiet_mode = "-q" in args or "--quiet" in args
    json_output = "--json" in args

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
            "--no-color",
            "-q",
            "--quiet",
            "--json",
        ):
            print(f"Error: Unknown option '{arg}'", file=sys.stderr)
            print("Run 'forge --help' for usage information", file=sys.stderr)
            return 1

    # Check for piped stdin (non-interactive input)
    stdin_input: str | None = None
    if not sys.stdin.isatty():
        try:
            stdin_input = sys.stdin.read().strip()
            if stdin_input:
                logger.debug("Read %d chars from stdin", len(stdin_input))
        except UnicodeDecodeError as e:
            print(f"Error: Invalid encoding in stdin: {e}", file=sys.stderr)
            print("Hint: Ensure input is valid UTF-8", file=sys.stderr)
            return 1

    # Load configuration
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_all()
    except Exception as e:
        logger.exception("Failed to load configuration")
        print(f"Error: Failed to load configuration: {e}", file=sys.stderr)
        print(
            "Hint: Check your config files at ~/.forge/settings.json or "
            ".forge/settings.json",
            file=sys.stderr,
        )
        return 1

    # Apply CLI flag overrides to config
    if no_color:
        config.display.color = False
    if quiet_mode:
        config.display.quiet = True
    if json_output:
        config.display.json_output = True

    # Check for API key - run setup wizard if not configured
    api_key = os.environ.get("OPENROUTER_API_KEY") or config.get_api_key()
    if not api_key:
        from code_forge.cli.setup import run_setup_wizard
        api_key = run_setup_wizard()
        if not api_key:
            return 1  # User cancelled setup

    # Start REPL or process stdin
    try:
        repl = CodeForgeREPL(config)
        return asyncio.run(run_with_agent(repl, config, api_key, stdin_input=stdin_input))
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.exception("REPL error")
        print(f"Error: {e}", file=sys.stderr)
        print(
            "Hint: For debugging, run with FORGE_LOG_LEVEL=DEBUG environment variable",
            file=sys.stderr,
        )
        return 1


async def run_with_agent(
    repl: CodeForgeREPL,
    config: CodeForgeConfig,
    api_key: str,
    stdin_input: str | None = None,
    *,
    deps: Dependencies | None = None,
) -> int:
    """Run REPL with agent and command handling.

    Args:
        repl: The REPL instance.
        config: Application configuration.
        api_key: OpenRouter API key.
        stdin_input: Optional input from stdin (batch mode).
        deps: Optional pre-configured dependencies (for testing).

    Returns:
        Exit code.
    """
    from code_forge.langchain.tools import adapt_tools_for_langchain
    from code_forge.modes import ModeName, ModeContext

    # Create dependencies if not provided (allows injection for testing)
    if deps is None:
        deps = Dependencies.create(config, api_key)

    # Auto-index project if RAG is enabled with auto_index
    if deps.rag_manager is not None and config.rag.auto_index:
        try:
            # Check if index needs building
            status = await deps.rag_manager.get_status()
            if not status.indexed:
                logger.info("Auto-indexing project for RAG...")
                repl.output.print_dim("Indexing project for semantic search...")
                await deps.rag_manager.index_project()
                repl.output.print_dim("Indexing complete.")
        except Exception as e:
            logger.warning(f"Auto-index failed: {e}")

    # Create RAG augmenter and processor if RAG is enabled
    rag_augmenter = None
    rag_processor = None
    if deps.rag_manager is not None and deps.rag_manager.is_enabled:
        from code_forge.rag.integration import RAGContextAugmenter, RAGMessageProcessor

        rag_processor = RAGMessageProcessor(deps.rag_manager)
        rag_augmenter = RAGContextAugmenter(deps.rag_manager)

    # Extract dependencies
    llm = deps.llm
    agent = deps.agent
    tool_registry = deps.tool_registry
    session_manager = deps.session_manager
    mode_manager = deps.mode_manager
    command_executor = deps.command_executor
    command_context = deps.command_context

    # Add repl to command context so commands can update status bar
    command_context.repl = repl

    # Update status bar with model info
    from code_forge.llm.routing import get_model_context_limit
    from code_forge.cli.context_adapter import ContextStatusAdapter

    model_context = get_model_context_limit(config.model.default)
    repl._status.set_model(config.model.default)
    repl._status.set_tokens(0, model_context)

    # Wire up context compression visibility to status bar
    if deps.context_manager:
        context_adapter = ContextStatusAdapter(
            status_bar=repl._status,
            context_manager=deps.context_manager,
        )
        logger.debug("ContextStatusAdapter attached for compression visibility")

    # Create mode context for mode switching
    def mode_output(msg: str) -> None:
        repl.output.print_dim(msg)

    mode_context_obj = ModeContext(output=mode_output)

    # Set system prompt to instruct the LLM to use tools
    from code_forge.llm.models import Message
    from code_forge.langchain.prompts import get_system_prompt

    raw_tools = [tool_registry.get(name) for name in tool_registry.list_names()]
    raw_tools = [t for t in raw_tools if t is not None]
    tools = adapt_tools_for_langchain(raw_tools)
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

    # Connect thinking toggle to mode manager with user feedback
    original_toggle = repl._toggle_thinking

    def thinking_toggle_with_mode() -> None:
        """Toggle thinking mode in both UI and mode manager.

        Wraps the original toggle to sync with mode manager and
        provides user feedback about the mode change.
        """
        original_toggle()
        # Switch mode based on new state and provide feedback
        if repl.thinking_enabled:
            mode_manager.switch_mode(ModeName.THINKING, mode_context_obj)
            repl._status.set_mode("Thinking")
            repl.output.print_dim("Thinking mode enabled (Ctrl+T to toggle)")
        else:
            mode_manager.switch_mode(ModeName.NORMAL, mode_context_obj)
            repl._status.set_mode("Normal")
            repl.output.print_dim("Thinking mode disabled (Ctrl+T to toggle)")
        # Update the system prompt
        update_system_prompt()

    # Wrap toggle function (preserves original for testing)
    repl._toggle_thinking = thinking_toggle_with_mode

    # Create session
    session = session_manager.create(title="CLI Session")

    # Track cumulative token usage (use list for mutable closure)
    total_tokens = [0]

    # Command timeout (30 seconds)
    COMMAND_TIMEOUT = 30.0

    # Register input handler
    async def handle_input(text: str) -> None:
        """Handle user input - route to commands or agent."""
        if text.startswith("/"):
            # Execute command with timeout
            try:
                cmd_result = await asyncio.wait_for(
                    command_executor.execute(text, command_context),
                    timeout=COMMAND_TIMEOUT,
                )
            except TimeoutError:
                repl.output.print_error(
                    f"Command timed out after {COMMAND_TIMEOUT}s. "
                    "Press Ctrl+C to interrupt if stuck."
                )
                return

            if cmd_result.output:
                repl.output.print(cmd_result.output)
            if cmd_result.error:
                # Use ErrorExplainer for friendly error messages
                explained = ErrorExplainer.explain(cmd_result.error)
                repl.output.print_error(explained)

            # Check for exit command
            if text.strip() in ("/exit", "/quit", "/q"):
                repl.stop()
        else:
            # Send to agent with streaming
            from code_forge.langchain.agent import AgentEventType
            from rich.status import Status

            # Check if we're in JSON output mode
            is_json_mode = repl.json_output
            is_quiet = repl.quiet_mode

            repl._status.set_status("Thinking...")

            # Initialize spinners before try block to avoid NameError in except/finally
            spinner = None
            tool_spinner = None

            # Track tool calls for JSON output
            tool_calls_log: list[dict] = []

            # Get interrupt handler for ESC key detection
            interrupt_handler = get_interrupt_handler()

            try:
                # Start interrupt monitoring (only in interactive mode with tty)
                if sys.stdin.isatty() and not is_json_mode:
                    await interrupt_handler.start_monitoring()
                    if not is_quiet:
                        repl.output.print_dim("(Press ESC twice to interrupt)")

                # Add user message to session
                session_manager.add_message("user", text)

                # Augment query with RAG context if applicable
                augmented_text = text
                if rag_processor is not None and rag_augmenter is not None:
                    if rag_processor.should_augment(text):
                        try:
                            context = await rag_augmenter.get_context_for_query(text)
                            if context:
                                # Prepend context to the user query
                                augmented_text = (
                                    f"<relevant_context>\n{context}\n</relevant_context>\n\n"
                                    f"User query: {text}"
                                )
                                if not is_quiet and not is_json_mode:
                                    repl.output.print_dim(
                                        f"(Enhanced with {len(context):,} chars of project context)"
                                    )
                        except Exception as e:
                            logger.warning(f"RAG augmentation failed: {e}")

                # Stream agent execution with real-time output
                accumulated_output = ""
                current_tool = None
                iteration_count = 0
                first_content_received = False

                if not is_json_mode:
                    repl.output.print("")  # Start on new line

                # Start with a spinner until we get content (skip in JSON mode)
                if not is_json_mode:
                    spinner = Status("[dim]Thinking...[/dim]", console=repl._console, spinner="dots")
                    spinner.start()

                async for event in agent.stream(augmented_text):
                    # Check for user interrupt (double-ESC)
                    if interrupt_handler.interrupted:
                        if not is_json_mode:
                            repl.output.print("")
                            repl.output.print_warning("Operation interrupted by user")
                        break

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
                                # Stop spinner on first content (not in JSON mode)
                                if not first_content_received:
                                    if spinner:
                                        spinner.stop()
                                    first_content_received = True
                                # Only print chunks in non-JSON mode
                                if not is_json_mode:
                                    repl._console.print(chunk, end="")
                                accumulated_output += chunk

                    elif event.type == AgentEventType.LLM_END:
                        pass  # Content already streamed

                    elif event.type == AgentEventType.TOOL_START:
                        # Stop thinking spinner if still running
                        if not first_content_received:
                            if spinner:
                                spinner.stop()
                            first_content_received = True

                        tool_name = event.data.get("name", "unknown")
                        tool_args = event.data.get("arguments", {})
                        current_tool = {"name": tool_name, "arguments": tool_args}

                        # Show tool call with formatted arguments (not in JSON mode)
                        if not is_json_mode:
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

                        # Log tool call for JSON output
                        if current_tool and isinstance(current_tool, dict):
                            tool_calls_log.append({
                                "name": current_tool["name"],
                                "arguments": current_tool["arguments"],
                                "result": result,
                                "success": success,
                                "duration": duration,
                            })

                        # Show truncated result (not in JSON mode)
                        if not is_json_mode:
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

                        # JSON output mode: emit structured response
                        if is_json_mode:
                            json_response = {
                                "response": accumulated_output,
                                "tool_calls": tool_calls_log,
                                "stats": {
                                    "iterations": iterations,
                                    "tool_count": tool_count,
                                    "duration": duration,
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": event_total_tokens,
                                },
                            }
                            print(json.dumps(json_response, indent=2))
                        # Normal mode: show stats (skip in quiet mode)
                        elif not is_quiet and (tool_count > 0 or event_total_tokens > 0):
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
                        if is_json_mode:
                            print(json.dumps({"error": error}, indent=2))
                        else:
                            # Use ErrorExplainer for friendly error messages
                            explained = ErrorExplainer.explain(str(error))
                            repl.output.print_error(f"Agent error: {explained}")

                if not is_json_mode:
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
                if is_json_mode:
                    print(json.dumps({"error": str(e)}, indent=2))
                else:
                    # Use ErrorExplainer for friendly error messages
                    explained = ErrorExplainer.explain(str(e))
                    repl.output.print_error(f"Error: {explained}")
            finally:
                # Stop interrupt monitoring
                await interrupt_handler.stop_monitoring()

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

    # Handle stdin input (batch mode)
    if stdin_input:
        logger.info("Processing stdin input in batch mode")
        await handle_input(stdin_input)
        return 0  # Exit after processing stdin

    # Run REPL (interactive mode)
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

Output Options:
  --no-color        Disable colored output
  -q, --quiet       Reduce output verbosity
  --json            Output responses in JSON format

For more information, visit: https://github.com/corey-rosamond/Code-Forge
"""
    print(help_text.strip())


if __name__ == "__main__":
    sys.exit(main())
