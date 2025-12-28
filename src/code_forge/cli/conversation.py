"""Conversational presentation layer for CLI output.

This module provides a natural language wrapper around tool execution events,
making the CLI feel more like a conversation with Claude Code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from rich.console import Console


@dataclass
class ToolDescription:
    """Description for a tool's action and completion messages."""

    action: str  # Present continuous, e.g., "Reading"
    completion: str  # Past/status, e.g., "File contents loaded"
    error: str = "Operation failed"  # Default error message


class ToolDescriptor:
    """Provides natural language descriptions for tools."""

    DESCRIPTIONS: ClassVar[dict[str, ToolDescription]] = {
        "Read": ToolDescription(
            action="Reading",
            completion="File contents loaded",
            error="Could not read file",
        ),
        "Write": ToolDescription(
            action="Writing to",
            completion="File saved",
            error="Could not write file",
        ),
        "Edit": ToolDescription(
            action="Editing",
            completion="Changes applied",
            error="Edit failed",
        ),
        "Bash": ToolDescription(
            action="Running",
            completion="Command completed",
            error="Command failed",
        ),
        "Glob": ToolDescription(
            action="Finding files matching",
            completion="Files found",
            error="Search failed",
        ),
        "Grep": ToolDescription(
            action="Searching for",
            completion="Search complete",
            error="Search failed",
        ),
        "WebSearch": ToolDescription(
            action="Searching the web for",
            completion="Search results ready",
            error="Web search failed",
        ),
        "WebFetch": ToolDescription(
            action="Fetching",
            completion="Page loaded",
            error="Could not fetch URL",
        ),
        "Task": ToolDescription(
            action="Starting task:",
            completion="Task complete",
            error="Task failed",
        ),
        "TodoWrite": ToolDescription(
            action="Updating task list",
            completion="Tasks updated",
            error="Failed to update tasks",
        ),
    }

    @classmethod
    def get_action(cls, tool_name: str, args: dict[str, Any]) -> str:
        """Get the action message for a tool.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Natural language action description.
        """
        desc = cls.DESCRIPTIONS.get(tool_name)
        if not desc:
            return f"Running {tool_name}..."

        # Extract key argument for context
        context = cls._extract_context(tool_name, args)
        if context:
            return f"{desc.action} {context}..."
        return f"{desc.action}..."

    @classmethod
    def get_completion(cls, tool_name: str, success: bool, duration: float) -> str:
        """Get the completion message for a tool.

        Args:
            tool_name: Name of the tool.
            success: Whether the operation succeeded.
            duration: Duration in seconds.

        Returns:
            Natural language completion description.
        """
        desc = cls.DESCRIPTIONS.get(tool_name)
        if not desc:
            status = "Complete" if success else "Failed"
            return f"{status} ({duration:.1f}s)"

        message = desc.completion if success else desc.error
        return f"{message} ({duration:.1f}s)"

    @classmethod
    def _extract_context(cls, tool_name: str, args: dict[str, Any]) -> str | None:
        """Extract context from arguments for display.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Returns:
            Context string or None.
        """
        # File operations - show filename
        if tool_name in ("Read", "Write", "Edit"):
            file_path = args.get("file_path", "")
            if file_path:
                # Extract just the filename
                parts = file_path.replace("\\", "/").split("/")
                return parts[-1] if parts else file_path

        # Search operations - show pattern/query
        if tool_name == "Grep":
            return args.get("pattern", "")[:50]
        if tool_name == "Glob":
            return args.get("pattern", "")
        if tool_name == "WebSearch":
            return args.get("query", "")[:50]

        # Bash - show truncated command
        if tool_name == "Bash":
            cmd = args.get("command", "")
            if len(cmd) > 40:
                return cmd[:37] + "..."
            return cmd

        # WebFetch - show URL
        if tool_name == "WebFetch":
            url = args.get("url", "")
            # Extract domain
            match = re.search(r"https?://([^/]+)", url)
            if match:
                return match.group(1)
            return url[:50] if url else None

        return None


class ReasoningExtractor:
    """Extracts reasoning/intent from LLM output."""

    REASONING_PATTERNS: ClassVar[list[str]] = [
        r"^(?:I'll|I will|Let me|First,?|Now,?|Next,?)",
        r"^(?:Looking at|Checking|Reading|Searching|Examining)",
        r"^(?:To do this|To accomplish this|In order to)",
        r"^(?:Based on|Given|Since)",
    ]

    @classmethod
    def looks_like_reasoning(cls, text: str) -> bool:
        """Check if text looks like reasoning/intent.

        Args:
            text: Text to check.

        Returns:
            True if text appears to be reasoning.
        """
        text = text.strip()
        for pattern in cls.REASONING_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def extract_reasoning(cls, text: str) -> tuple[str | None, str]:
        """Extract reasoning from the start of text.

        Args:
            text: Full text that may contain reasoning.

        Returns:
            Tuple of (reasoning, remaining_text).
        """
        lines = text.split("\n", 1)
        first_line = lines[0].strip()

        if cls.looks_like_reasoning(first_line):
            remaining = lines[1] if len(lines) > 1 else ""
            return first_line, remaining.strip()

        return None, text


class ErrorExplainer:
    """Provides friendly error explanations.

    The ERROR_CATALOG contains patterns organized by category:
    - File System: File not found, permission denied, disk full, etc.
    - Python: Import, syntax, type, attribute errors
    - Node.js/npm: Module not found, version conflicts
    - Git: Not a repo, merge conflicts, push rejected
    - Network: Connection refused, DNS, SSL, timeout
    - Shell: Command not found, exit codes
    - API: Rate limiting, authentication, quota
    """

    ERROR_CATALOG: ClassVar[dict[str, dict[str, Any]]] = {
        # ===== FILE SYSTEM ERRORS =====
        "File not found": {
            "explanation": "The file doesn't exist at that location",
            "suggestions": [
                "Check the file path spelling",
                "Use Glob to search for the file",
                "Verify the file wasn't recently moved or deleted",
            ],
        },
        "Permission denied": {
            "explanation": "Cannot access this file due to permissions",
            "suggestions": [
                "Check file permissions with 'ls -la'",
                "You may need elevated access (sudo)",
                "Verify you own the file or have group access",
            ],
        },
        "No such file or directory": {
            "explanation": "The path doesn't exist",
            "suggestions": [
                "Create the directory with 'mkdir -p'",
                "Check the path spelling",
                "Use absolute paths to avoid working directory issues",
            ],
        },
        "Is a directory": {
            "explanation": "Expected a file but found a directory",
            "suggestions": [
                "Check if you meant to use a file path",
                "List directory contents with 'ls'",
            ],
        },
        "Not a directory": {
            "explanation": "Expected a directory but found a file",
            "suggestions": [
                "Check if you meant to use a directory path",
                "Use dirname to get the parent directory",
            ],
        },
        "No space left on device": {
            "explanation": "The disk is full",
            "suggestions": [
                "Free up disk space by removing unused files",
                "Check disk usage with 'df -h'",
                "Clear temp files and caches",
            ],
        },
        "Too many open files": {
            "explanation": "The process has exceeded its file descriptor limit",
            "suggestions": [
                "Close unused file handles",
                "Increase ulimit with 'ulimit -n 4096'",
                "Check for file handle leaks in your code",
            ],
        },
        "Read-only file system": {
            "explanation": "The filesystem is mounted as read-only",
            "suggestions": [
                "Remount the filesystem with write permissions",
                "Check if the disk is failing",
                "Write to a different location",
            ],
        },
        "File exists": {
            "explanation": "Cannot create file because it already exists",
            "suggestions": [
                "Use overwrite mode or remove the existing file",
                "Rename the new file to avoid conflict",
            ],
        },
        "Directory not empty": {
            "explanation": "Cannot remove directory because it has contents",
            "suggestions": [
                "Use 'rm -rf' to remove recursively (carefully!)",
                "Remove contents first, then the directory",
            ],
        },
        # ===== PYTHON ERRORS =====
        "ModuleNotFoundError": {
            "explanation": "A Python module/package is not installed",
            "suggestions": [
                "Install with 'pip install <package>'",
                "Check if you're in the right virtual environment",
                "Verify the package name spelling",
            ],
        },
        "ImportError": {
            "explanation": "Cannot import a Python module or specific name",
            "suggestions": [
                "Check the import statement spelling",
                "Verify the module is installed correctly",
                "Check for circular import issues",
            ],
        },
        "SyntaxError": {
            "explanation": "Invalid Python syntax",
            "suggestions": [
                "Check for missing colons, parentheses, or quotes",
                "Look at the line number indicated in the error",
                "Ensure proper indentation",
            ],
        },
        "IndentationError": {
            "explanation": "Inconsistent indentation in Python code",
            "suggestions": [
                "Use consistent spaces or tabs (not mixed)",
                "Configure your editor to use 4 spaces per indent",
                "Check the line indicated in the error",
            ],
        },
        "TypeError": {
            "explanation": "Operation applied to wrong type",
            "suggestions": [
                "Check the types of variables being used",
                "Use type() to inspect variable types",
                "Ensure function arguments match expected types",
            ],
        },
        "AttributeError": {
            "explanation": "Object doesn't have the requested attribute/method",
            "suggestions": [
                "Check the spelling of the attribute name",
                "Verify the object is the expected type",
                "Use dir() to see available attributes",
            ],
        },
        "KeyError": {
            "explanation": "Dictionary key doesn't exist",
            "suggestions": [
                "Use .get(key, default) for safe access",
                "Check if the key exists with 'in' operator",
                "Verify the key spelling and type",
            ],
        },
        "IndexError": {
            "explanation": "List/sequence index out of range",
            "suggestions": [
                "Check the length of the sequence with len()",
                "Use try/except or check bounds before indexing",
                "Remember Python uses 0-based indexing",
            ],
        },
        "ValueError": {
            "explanation": "Function received correct type but inappropriate value",
            "suggestions": [
                "Check the value being passed",
                "Validate input before passing to functions",
                "Review the function's expected value range",
            ],
        },
        "NameError": {
            "explanation": "Variable or name is not defined",
            "suggestions": [
                "Check the variable spelling",
                "Ensure the variable is defined before use",
                "Check the scope - is it defined in this context?",
            ],
        },
        "RecursionError": {
            "explanation": "Maximum recursion depth exceeded",
            "suggestions": [
                "Check for infinite recursion in your code",
                "Add a base case to stop recursion",
                "Consider using iteration instead",
            ],
        },
        "StopIteration": {
            "explanation": "Iterator has no more items",
            "suggestions": [
                "Use a for loop instead of manual iteration",
                "Check if the iterator is exhausted",
            ],
        },
        # ===== NODE.JS / NPM ERRORS =====
        "MODULE_NOT_FOUND": {
            "explanation": "A Node.js module is not installed",
            "suggestions": [
                "Run 'npm install' to install dependencies",
                "Install the specific package with 'npm install <package>'",
                "Check package.json for the dependency",
            ],
        },
        "ENOENT": {
            "explanation": "File or directory not found (Node.js)",
            "suggestions": [
                "Check the path exists",
                "Use path.resolve() for absolute paths",
                "Create missing directories with fs.mkdirSync",
            ],
        },
        "EACCES": {
            "explanation": "Permission denied (Node.js)",
            "suggestions": [
                "Don't use sudo with npm - fix npm permissions instead",
                "Change ownership of the directory",
                "Use a different installation location",
            ],
        },
        "EADDRINUSE": {
            "explanation": "Port is already in use",
            "suggestions": [
                "Use a different port",
                "Find and stop the process using the port: 'lsof -i :PORT'",
                "Wait for the port to be released",
            ],
        },
        "npm ERR! peer dep": {
            "explanation": "Peer dependency conflict between packages",
            "suggestions": [
                "Try 'npm install --legacy-peer-deps'",
                "Update conflicting packages",
                "Check if packages are compatible",
            ],
        },
        "npm ERR! code E404": {
            "explanation": "npm package not found in registry",
            "suggestions": [
                "Check the package name spelling",
                "Verify the package exists on npmjs.com",
                "Check if the package is scoped (@org/package)",
            ],
        },
        "EPERM": {
            "explanation": "Operation not permitted (Node.js)",
            "suggestions": [
                "Close programs that may be using the files",
                "Check file/directory permissions",
                "On Windows, try running as administrator",
            ],
        },
        "ENOMEM": {
            "explanation": "Not enough memory",
            "suggestions": [
                "Close other applications to free memory",
                "Increase Node.js memory with --max-old-space-size",
                "Process data in smaller chunks",
            ],
        },
        # ===== GIT ERRORS =====
        "not a git repository": {
            "explanation": "The current directory is not a Git repository",
            "suggestions": [
                "Initialize with 'git init'",
                "Navigate to the correct project directory",
                "Clone an existing repository",
            ],
        },
        "CONFLICT": {
            "explanation": "Merge conflict - same lines modified in both branches",
            "suggestions": [
                "Edit the conflicting files to resolve",
                "Use 'git diff' to see the conflicts",
                "After resolving, run 'git add' and 'git commit'",
            ],
        },
        "merge conflict": {
            "explanation": "Git couldn't automatically merge changes",
            "suggestions": [
                "Open the file and look for <<<<<<< markers",
                "Choose which version to keep",
                "Stage resolved files with 'git add'",
            ],
        },
        "rejected": {
            "explanation": "Push rejected - remote has changes you don't have",
            "suggestions": [
                "Pull first with 'git pull'",
                "Resolve any merge conflicts",
                "Then push again",
            ],
        },
        "non-fast-forward": {
            "explanation": "Cannot push because remote has diverged",
            "suggestions": [
                "Pull and merge/rebase first",
                "Never force push to shared branches",
                "Use 'git pull --rebase' for cleaner history",
            ],
        },
        "detached HEAD": {
            "explanation": "Not on a branch - commits won't be saved to any branch",
            "suggestions": [
                "Create a branch with 'git checkout -b <name>'",
                "Or checkout an existing branch",
                "Save your work before switching branches",
            ],
        },
        "fatal: refusing to merge unrelated histories": {
            "explanation": "Trying to merge repositories with no common history",
            "suggestions": [
                "Use '--allow-unrelated-histories' flag",
                "Consider if this is really what you want",
            ],
        },
        "error: Your local changes": {
            "explanation": "Uncommitted changes would be overwritten",
            "suggestions": [
                "Commit your changes first",
                "Or stash them with 'git stash'",
                "Or discard with 'git checkout -- .'",
            ],
        },
        # ===== NETWORK / HTTP ERRORS =====
        "Connection refused": {
            "explanation": "Could not connect to the server",
            "suggestions": [
                "Check if the service is running",
                "Verify the URL/host and port are correct",
                "Check firewall settings",
            ],
        },
        "timed out": {
            "explanation": "The operation took too long to complete",
            "suggestions": [
                "Check your network connection",
                "The server may be slow or overloaded",
                "Try again in a few moments",
            ],
        },
        "Connection reset": {
            "explanation": "The connection was forcibly closed",
            "suggestions": [
                "Check your network stability",
                "The server may have crashed or restarted",
                "Try again after a short wait",
            ],
        },
        "Name or service not known": {
            "explanation": "DNS lookup failed - hostname not found",
            "suggestions": [
                "Check the hostname spelling",
                "Verify your DNS settings",
                "Check your internet connection",
            ],
        },
        "getaddrinfo": {
            "explanation": "DNS resolution failed",
            "suggestions": [
                "Check internet connectivity",
                "Verify the hostname is correct",
                "Try using an IP address instead",
            ],
        },
        "SSL": {
            "explanation": "SSL/TLS certificate error",
            "suggestions": [
                "Check if the certificate is expired",
                "Verify the hostname matches the certificate",
                "Update your CA certificates",
            ],
        },
        "certificate verify failed": {
            "explanation": "SSL certificate validation failed",
            "suggestions": [
                "Check if the certificate is self-signed",
                "Update your system's CA certificates",
                "Verify the date/time on your system is correct",
            ],
        },
        "HTTP 401": {
            "explanation": "Authentication required or failed",
            "suggestions": [
                "Check your credentials/API key",
                "Ensure the token hasn't expired",
                "Verify you have access to this resource",
            ],
        },
        "HTTP 403": {
            "explanation": "Access forbidden",
            "suggestions": [
                "Check your permissions for this resource",
                "Verify your account has the required access level",
                "The resource may require different credentials",
            ],
        },
        "HTTP 404": {
            "explanation": "Resource not found",
            "suggestions": [
                "Check the URL spelling",
                "Verify the resource still exists",
                "Check if the API version has changed",
            ],
        },
        "HTTP 429": {
            "explanation": "Too many requests - rate limited",
            "suggestions": [
                "Wait before making more requests",
                "Implement request throttling",
                "Check the API rate limit documentation",
            ],
        },
        "HTTP 500": {
            "explanation": "Internal server error",
            "suggestions": [
                "The server encountered an error",
                "Try again later",
                "Check if the service is experiencing issues",
            ],
        },
        "HTTP 502": {
            "explanation": "Bad gateway - upstream server error",
            "suggestions": [
                "The upstream server is unreachable",
                "Wait and try again",
                "Check if the service is down",
            ],
        },
        "HTTP 503": {
            "explanation": "Service unavailable",
            "suggestions": [
                "The service is temporarily unavailable",
                "Wait and try again later",
                "Check the service status page",
            ],
        },
        # ===== SHELL / COMMAND ERRORS =====
        "Command not found": {
            "explanation": "The program isn't installed or not in PATH",
            "suggestions": [
                "Install the required tool",
                "Check if it's in your PATH: 'echo $PATH'",
                "Use the full path to the executable",
            ],
        },
        "exit code 1": {
            "explanation": "Command failed with general error",
            "suggestions": [
                "Check the command output for error messages",
                "Verify the command arguments are correct",
                "Run the command manually for more details",
            ],
        },
        "exit code 2": {
            "explanation": "Command misuse or invalid arguments",
            "suggestions": [
                "Check the command syntax with --help",
                "Verify all required arguments are provided",
                "Check for typos in options",
            ],
        },
        "exit code 126": {
            "explanation": "Command found but not executable",
            "suggestions": [
                "Make the file executable: 'chmod +x file'",
                "Check file permissions",
            ],
        },
        "exit code 127": {
            "explanation": "Command not found",
            "suggestions": [
                "Install the required command",
                "Check the spelling",
                "Verify PATH environment variable",
            ],
        },
        "exit code 128": {
            "explanation": "Invalid exit code argument",
            "suggestions": [
                "This usually indicates a script error",
                "Check the script's exit statements",
            ],
        },
        "exit code 130": {
            "explanation": "Script terminated by Ctrl+C (SIGINT)",
            "suggestions": [
                "The command was interrupted",
                "This is normal if you pressed Ctrl+C",
            ],
        },
        "Killed": {
            "explanation": "Process was killed (likely out of memory)",
            "suggestions": [
                "The process ran out of memory",
                "Try processing smaller data sets",
                "Close other applications to free memory",
            ],
        },
        "Segmentation fault": {
            "explanation": "Program crashed due to memory access violation",
            "suggestions": [
                "This is usually a bug in the program",
                "Check for buffer overflows or null pointers",
                "Try updating the software",
            ],
        },
        # ===== API / SERVICE ERRORS =====
        "rate limit": {
            "explanation": "Too many API requests",
            "suggestions": [
                "Wait before making more requests",
                "Implement exponential backoff",
                "Consider caching responses",
            ],
        },
        "quota exceeded": {
            "explanation": "Usage quota has been exceeded",
            "suggestions": [
                "Check your usage in the service dashboard",
                "Wait for the quota to reset",
                "Consider upgrading your plan",
            ],
        },
        "invalid api key": {
            "explanation": "The API key is invalid or expired",
            "suggestions": [
                "Check the API key in your environment/config",
                "Generate a new API key",
                "Verify the key has the required permissions",
            ],
        },
        "unauthorized": {
            "explanation": "Authentication is required or failed",
            "suggestions": [
                "Check your credentials",
                "Ensure the token hasn't expired",
                "Re-authenticate if needed",
            ],
        },
        "invalid json": {
            "explanation": "Malformed JSON in request or response",
            "suggestions": [
                "Validate your JSON with a linter",
                "Check for trailing commas or missing quotes",
                "Ensure proper escaping of special characters",
            ],
        },
        # ===== DOCKER ERRORS =====
        "docker: Error response from daemon": {
            "explanation": "Docker daemon returned an error",
            "suggestions": [
                "Check if Docker daemon is running",
                "Verify you have permission to access Docker",
                "Check Docker logs for details",
            ],
        },
        "image not found": {
            "explanation": "Docker image doesn't exist",
            "suggestions": [
                "Pull the image with 'docker pull'",
                "Check the image name and tag spelling",
                "Verify the registry URL is correct",
            ],
        },
        "port is already allocated": {
            "explanation": "Container port conflicts with existing binding",
            "suggestions": [
                "Use a different host port mapping",
                "Stop the container using that port",
                "Use 'docker ps' to see running containers",
            ],
        },
        # ===== DATABASE ERRORS =====
        "connection refused": {
            "explanation": "Cannot connect to the database",
            "suggestions": [
                "Check if the database server is running",
                "Verify the connection string/host/port",
                "Check firewall and network settings",
            ],
        },
        "authentication failed": {
            "explanation": "Database login credentials are incorrect",
            "suggestions": [
                "Verify username and password",
                "Check if the user has access to the database",
                "Review connection string format",
            ],
        },
        "duplicate key": {
            "explanation": "Trying to insert a record that already exists",
            "suggestions": [
                "Check for existing records before inserting",
                "Use UPSERT or ON CONFLICT if available",
                "Verify your unique constraints",
            ],
        },
    }

    @classmethod
    def explain(cls, error: str) -> str:
        """Get a friendly explanation for an error.

        Args:
            error: Error message to explain.

        Returns:
            Friendly explanation with suggestions.
        """
        error_lower = error.lower()

        for pattern, info in cls.ERROR_CATALOG.items():
            if pattern.lower() in error_lower:
                lines = [info["explanation"]]
                if info.get("suggestions"):
                    lines.append("")
                    lines.append("Try:")
                    for suggestion in info["suggestions"]:
                        lines.append(f"  - {suggestion}")
                return "\n".join(lines)

        # Default: just return the original error
        return error


class ConversationalPresenter:
    """Presents tool execution events in a conversational style.

    This class wraps the raw agent events and presents them in a more
    natural, conversational way - similar to how Claude Code displays
    its actions.

    Example:
        presenter = ConversationalPresenter(console)

        # When tool starts:
        presenter.present_tool_start("Read", {"file_path": "/app/config.py"})
        # Output: "Reading config.py..."

        # When tool ends:
        presenter.present_tool_end("Read", True, 0.2)
        # Output: "File contents loaded (0.2s)"
    """

    def __init__(self, console: Console, *, verbose: bool = False) -> None:
        """Initialize the presenter.

        Args:
            console: Rich console for output.
            verbose: If True, show more details.
        """
        self._console = console
        self._verbose = verbose
        self._accumulated_text = ""
        self._current_tool: str | None = None

    def present_tool_start(self, tool_name: str, args: dict[str, Any]) -> None:
        """Present a tool start event.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.
        """
        self._current_tool = tool_name
        action = ToolDescriptor.get_action(tool_name, args)
        self._console.print(f"[dim]{action}[/dim]")

    def present_tool_end(
        self,
        tool_name: str,
        success: bool,
        duration: float,
        result: str = "",
    ) -> None:
        """Present a tool end event.

        Args:
            tool_name: Name of the tool.
            success: Whether the operation succeeded.
            duration: Duration in seconds.
            result: Tool result (optional, for showing preview).
        """
        completion = ToolDescriptor.get_completion(tool_name, success, duration)

        if success:
            # Show result preview for certain tools
            if result and tool_name in ("Read", "Grep", "Glob"):
                preview = self._truncate_output(result, max_lines=3)
                if preview:
                    self._console.print(f"[dim]{preview}[/dim]")

            self._console.print(f"[green]{completion}[/green]")
        else:
            self._console.print(f"[red]{completion}[/red]")

        self._current_tool = None

    def present_error(self, error: str) -> None:
        """Present an error with friendly explanation.

        Args:
            error: Error message.
        """
        explanation = ErrorExplainer.explain(error)
        self._console.print(f"[red]Error: {explanation}[/red]")

    def accumulate_text(self, chunk: str) -> None:
        """Accumulate text chunks for reasoning extraction.

        Args:
            chunk: Text chunk to accumulate.
        """
        self._accumulated_text += chunk

    def get_accumulated_text(self) -> str:
        """Get and clear accumulated text.

        Returns:
            Accumulated text.
        """
        text = self._accumulated_text
        self._accumulated_text = ""
        return text

    def present_reasoning(self, text: str) -> str | None:
        """Extract and present reasoning from text.

        Args:
            text: Text that may contain reasoning.

        Returns:
            Reasoning if found, None otherwise.
        """
        reasoning, _ = ReasoningExtractor.extract_reasoning(text)
        if reasoning:
            self._console.print(f"[italic dim]{reasoning}[/italic dim]")
        return reasoning

    def _truncate_output(self, text: str, max_lines: int = 5) -> str:
        """Truncate output for preview.

        Args:
            text: Text to truncate.
            max_lines: Maximum lines to show.

        Returns:
            Truncated text.
        """
        if not text:
            return ""

        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text

        shown = lines[:max_lines]
        remaining = len(lines) - max_lines
        return "\n".join(shown) + f"\n... ({remaining} more lines)"
