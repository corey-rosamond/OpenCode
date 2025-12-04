"""
Headless mode implementation.

Provides non-interactive execution for automation,
CI/CD integration, and scripting.
"""

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import IO, Any

from .base import Mode, ModeConfig, ModeContext, ModeName
from .prompts import HEADLESS_MODE_PROMPT


class OutputFormat(Enum):
    """Output format options."""

    TEXT = "text"
    JSON = "json"


@dataclass
class HeadlessConfig:
    """Configuration for headless mode.

    Attributes:
        input_file: Path to input file (None for stdin)
        output_file: Path to output file (None for stdout)
        output_format: Format for output (text or json)
        timeout: Maximum execution time in seconds
        auto_approve_safe: Auto-approve safe operations
        fail_on_unsafe: Fail on unsafe operations
        exit_on_complete: Exit process when done
    """

    input_file: str | None = None
    output_file: str | None = None
    output_format: OutputFormat = OutputFormat.TEXT
    timeout: int = 300
    auto_approve_safe: bool = True
    fail_on_unsafe: bool = True
    exit_on_complete: bool = True


@dataclass
class HeadlessResult:
    """Result of headless execution.

    Provides structured output for automation.

    Attributes:
        success: Whether execution succeeded
        message: Human-readable summary
        output: Full output text
        error: Error message if failed
        exit_code: Process exit code
        execution_time: Time taken in seconds
        details: Additional result details
        timestamp: When result was created
    """

    success: bool
    message: str
    output: str = ""
    error: str | None = None
    exit_code: int = 0
    execution_time: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON representation
        """
        return json.dumps(
            {
                "status": "success" if self.success else "failure",
                "message": self.message,
                "output": self.output,
                "error": self.error,
                "exit_code": self.exit_code,
                "execution_time": self.execution_time,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
            },
            indent=2,
        )

    def to_text(self) -> str:
        """Convert to text format.

        Returns:
            Text representation
        """
        lines = [self.message]
        if self.output:
            lines.extend(["", self.output])
        if self.error:
            lines.extend(["", f"Error: {self.error}"])
        if self.details:
            lines.extend(["", "Details:"])
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "success": self.success,
            "message": self.message,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HeadlessResult":
        """Deserialize from dictionary.

        Args:
            data: Dictionary to deserialize from

        Returns:
            HeadlessResult instance
        """
        return cls(
            success=data["success"],
            message=data["message"],
            output=data.get("output", ""),
            error=data.get("error"),
            exit_code=data.get("exit_code", 0),
            execution_time=data.get("execution_time", 0.0),
            details=data.get("details", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
        )


class HeadlessMode(Mode):
    """Non-interactive mode for automation.

    Runs without user prompts, suitable for CI/CD
    pipelines and scripting.
    """

    def __init__(
        self,
        config: ModeConfig | None = None,
        headless_config: HeadlessConfig | None = None,
    ) -> None:
        """Initialize headless mode.

        Args:
            config: Optional mode configuration
            headless_config: Optional headless-specific configuration
        """
        super().__init__(config)
        self.headless_config = headless_config or HeadlessConfig()
        self._start_time: float | None = None
        self._input_stream: IO[str] | None = None
        self._output_stream: IO[str] | None = None
        self._owns_input_stream: bool = False
        self._owns_output_stream: bool = False

    @property
    def name(self) -> ModeName:
        """Return mode name.

        Returns:
            ModeName.HEADLESS
        """
        return ModeName.HEADLESS

    def _default_config(self) -> ModeConfig:
        """Return default configuration for headless mode.

        Returns:
            ModeConfig with headless mode prompt
        """
        return ModeConfig(
            name=ModeName.HEADLESS,
            description="Non-interactive automation mode",
            system_prompt_addition=HEADLESS_MODE_PROMPT,
        )

    def activate(self, context: ModeContext) -> None:
        """Enter headless mode.

        Args:
            context: Mode context

        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        super().activate(context)
        self._start_time = time.time()

        # Open input stream
        if self.headless_config.input_file:
            path = Path(self.headless_config.input_file)
            if not path.exists():
                raise FileNotFoundError(f"Input file not found: {path}")
            self._input_stream = path.open(encoding="utf-8")
            self._owns_input_stream = True
        else:
            self._input_stream = sys.stdin
            self._owns_input_stream = False

        # Open output stream
        if self.headless_config.output_file:
            path = Path(self.headless_config.output_file)
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            self._output_stream = path.open("w", encoding="utf-8")
            self._owns_output_stream = True
        else:
            self._output_stream = sys.stdout
            self._owns_output_stream = False

    def deactivate(self, context: ModeContext) -> None:
        """Exit headless mode.

        Args:
            context: Mode context
        """
        # Close file streams if we own them
        if self._owns_input_stream and self._input_stream:
            self._input_stream.close()
        if self._owns_output_stream and self._output_stream:
            self._output_stream.close()

        self._input_stream = None
        self._output_stream = None
        self._owns_input_stream = False
        self._owns_output_stream = False
        self._start_time = None
        super().deactivate(context)

    def read_input(self) -> str:
        """Read input from configured source.

        Returns:
            Input text
        """
        if self._input_stream:
            return self._input_stream.read()
        return ""

    def write_output(self, result: HeadlessResult) -> None:
        """Write output to configured destination.

        Args:
            result: Execution result to output
        """
        if not self._output_stream:
            return

        if self.headless_config.output_format == OutputFormat.JSON:
            output = result.to_json()
        else:
            output = result.to_text()

        self._output_stream.write(output)
        self._output_stream.write("\n")
        self._output_stream.flush()

    def handle_permission_request(
        self,
        operation: str,  # noqa: ARG002
        is_safe: bool,
    ) -> bool:
        """Handle permission request non-interactively.

        Args:
            operation: Description of operation
            is_safe: Whether operation is considered safe

        Returns:
            True if operation approved, False if denied
        """
        if is_safe and self.headless_config.auto_approve_safe:
            return True

        if not is_safe and self.headless_config.fail_on_unsafe:
            return False

        # Default to deny for ambiguous cases
        return False

    def create_result(
        self,
        success: bool,
        message: str,
        output: str = "",
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> HeadlessResult:
        """Create a headless execution result.

        Args:
            success: Whether execution succeeded
            message: Summary message
            output: Full output text
            error: Error message if failed
            details: Additional details

        Returns:
            HeadlessResult instance
        """
        elapsed = time.time() - self._start_time if self._start_time else 0.0

        return HeadlessResult(
            success=success,
            message=message,
            output=output,
            error=error,
            exit_code=0 if success else 1,
            execution_time=elapsed,
            details=details or {},
        )

    def modify_response(self, response: str) -> str:
        """Format response for headless output.

        Args:
            response: Raw response text

        Returns:
            Formatted response
        """
        # In headless mode, responses may need JSON formatting
        if self.headless_config.output_format == OutputFormat.JSON:
            result = self.create_result(
                success=True,
                message="Completed",
                output=response,
            )
            return result.to_json()
        return response

    def check_timeout(self) -> bool:
        """Check if execution has exceeded timeout.

        Returns:
            True if timed out
        """
        if not self._start_time:
            return False
        elapsed = time.time() - self._start_time
        return elapsed > self.headless_config.timeout


def create_headless_config_from_args(
    input_file: str | None = None,
    output_file: str | None = None,
    json_output: bool = False,
    timeout: int = 300,
) -> HeadlessConfig:
    """Create headless config from CLI arguments.

    Args:
        input_file: Path to input file
        output_file: Path to output file
        json_output: Whether to use JSON output format
        timeout: Execution timeout in seconds

    Returns:
        HeadlessConfig instance
    """
    return HeadlessConfig(
        input_file=input_file,
        output_file=output_file,
        output_format=OutputFormat.JSON if json_output else OutputFormat.TEXT,
        timeout=timeout,
    )
