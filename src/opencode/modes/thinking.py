"""
Thinking mode implementation.

Provides extended reasoning capabilities with visible
thinking process and structured analysis.
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import Mode, ModeConfig, ModeContext, ModeName
from .prompts import THINKING_MODE_DEEP_PROMPT, THINKING_MODE_PROMPT


@dataclass
class ThinkingConfig:
    """Configuration for thinking mode.

    Attributes:
        max_thinking_tokens: Maximum tokens for thinking
        show_thinking: Whether to display thinking section
        thinking_style: Style of thinking (analytical, creative, thorough)
        deep_mode: Enable deep analysis mode
    """

    max_thinking_tokens: int = 10000
    show_thinking: bool = True
    thinking_style: str = "analytical"
    deep_mode: bool = False


@dataclass
class ThinkingResult:
    """Result of extended thinking.

    Separates thinking process from final response.

    Attributes:
        thinking: The thinking/reasoning content
        response: The final response content
        thinking_tokens: Token count for thinking section
        response_tokens: Token count for response section
        time_seconds: Time spent thinking
        timestamp: When thinking occurred
    """

    thinking: str
    response: str
    thinking_tokens: int = 0
    response_tokens: int = 0
    time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "thinking": self.thinking,
            "response": self.response,
            "thinking_tokens": self.thinking_tokens,
            "response_tokens": self.response_tokens,
            "time_seconds": self.time_seconds,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThinkingResult":
        """Deserialize from dictionary.

        Args:
            data: Dictionary to deserialize from

        Returns:
            ThinkingResult instance
        """
        return cls(
            thinking=data["thinking"],
            response=data["response"],
            thinking_tokens=data.get("thinking_tokens", 0),
            response_tokens=data.get("response_tokens", 0),
            time_seconds=data.get("time_seconds", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
        )


# Pattern to extract thinking and response sections
THINKING_PATTERN = re.compile(
    r"<thinking>\s*(.*?)\s*</thinking>\s*<response>\s*(.*?)\s*</response>",
    re.DOTALL | re.IGNORECASE,
)


class ThinkingMode(Mode):
    """Extended thinking mode for complex problems.

    Encourages structured reasoning and shows the
    thinking process alongside the final response.
    """

    def __init__(
        self,
        config: ModeConfig | None = None,
        thinking_config: ThinkingConfig | None = None,
    ) -> None:
        """Initialize thinking mode.

        Args:
            config: Optional mode configuration
            thinking_config: Optional thinking-specific configuration
        """
        super().__init__(config)
        self.thinking_config = thinking_config or ThinkingConfig()
        self._start_time: float | None = None

    @property
    def name(self) -> ModeName:
        """Return mode name.

        Returns:
            ModeName.THINKING
        """
        return ModeName.THINKING

    def _default_config(self) -> ModeConfig:
        """Return default configuration for thinking mode.

        Returns:
            ModeConfig with thinking mode prompt
        """
        return ModeConfig(
            name=ModeName.THINKING,
            description="Extended thinking mode",
            system_prompt_addition=THINKING_MODE_PROMPT,
        )

    def activate(self, context: ModeContext) -> None:
        """Enter thinking mode.

        Args:
            context: Mode context
        """
        super().activate(context)
        self._start_time = time.time()

        deep = self.thinking_config.deep_mode
        mode_type = "deep thinking" if deep else "thinking"

        context.output(f"Entered {mode_type} mode.")
        context.output("I'll show my reasoning process in detail.")

        # Update prompt for deep mode
        if deep:
            self._config = ModeConfig(
                name=ModeName.THINKING,
                description="Deep thinking mode",
                system_prompt_addition=THINKING_MODE_DEEP_PROMPT,
                enabled=self._config.enabled,
                settings=self._config.settings,
            )

    def deactivate(self, context: ModeContext) -> None:
        """Exit thinking mode.

        Args:
            context: Mode context
        """
        self._start_time = None
        super().deactivate(context)
        context.output("Exited thinking mode.")

    def set_deep_mode(self, enabled: bool) -> None:
        """Toggle deep thinking mode.

        Args:
            enabled: Whether to enable deep mode
        """
        self.thinking_config.deep_mode = enabled
        if enabled:
            self._config = ModeConfig(
                name=ModeName.THINKING,
                description="Deep thinking mode",
                system_prompt_addition=THINKING_MODE_DEEP_PROMPT,
                enabled=self._config.enabled,
                settings=self._config.settings,
            )
        else:
            self._config = ModeConfig(
                name=ModeName.THINKING,
                description="Extended thinking mode",
                system_prompt_addition=THINKING_MODE_PROMPT,
                enabled=self._config.enabled,
                settings=self._config.settings,
            )

    def set_thinking_budget(self, tokens: int) -> None:
        """Set maximum thinking tokens.

        Args:
            tokens: Maximum token budget (minimum 1000)
        """
        self.thinking_config.max_thinking_tokens = max(1000, tokens)

    def modify_response(self, response: str) -> str:
        """Extract and format thinking from response.

        Args:
            response: Raw response text

        Returns:
            Formatted response with thinking extracted
        """
        match = THINKING_PATTERN.search(response)

        if not match:
            # No structured thinking found
            return response

        thinking = match.group(1).strip()
        final_response = match.group(2).strip()

        # Create thinking result
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        result = ThinkingResult(
            thinking=thinking,
            response=final_response,
            time_seconds=elapsed,
        )

        # Store in state
        self._state.data["last_thinking"] = result.to_dict()

        # Format output based on config
        return self.format_thinking_output(result)

    def format_thinking_output(self, result: ThinkingResult) -> str:
        """Format thinking result for display.

        Args:
            result: Thinking result to format

        Returns:
            Formatted output string
        """
        lines: list[str] = []

        if self.thinking_config.show_thinking:
            lines.extend([
                "### Thinking Process",
                "",
                result.thinking,
                "",
                "---",
                "",
            ])

        lines.append(result.response)

        # Add timing info
        if result.time_seconds > 0:
            lines.extend([
                "",
                f"*Thinking time: {result.time_seconds:.1f}s*",
            ])

        return "\n".join(lines)

    def get_last_thinking(self) -> ThinkingResult | None:
        """Get the last thinking result.

        Returns:
            Last ThinkingResult or None if none exists
        """
        data = self._state.data.get("last_thinking")
        if data:
            return ThinkingResult.from_dict(data)
        return None


# Patterns for detecting complex problems
COMPLEX_PROBLEM_PATTERNS = [
    r"\bcomplex\b",
    r"\bdifficult\b",
    r"\btricky\b",
    r"\btrade-?offs?\b",
    r"\bweigh\b.*\boptions\b",
    r"\banalyze\b",
    r"\bcompare\b.*\bapproaches\b",
    r"\bpros?\s+and\s+cons?\b",
    r"\bthink\s+(through|about|carefully)\b",
    r"\breason\b.*\babout\b",
]


def should_suggest_thinking(message: str) -> bool:
    """Check if thinking mode might help with this message.

    Args:
        message: User message to check

    Returns:
        True if thinking mode might be helpful
    """
    message_lower = message.lower()
    return any(re.search(pattern, message_lower) for pattern in COMPLEX_PROBLEM_PATTERNS)
