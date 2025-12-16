"""Context limits and tracking."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .tokens import TokenCounter, get_counter

logger = logging.getLogger(__name__)


@dataclass
class ContextBudget:
    """Token budget allocation for different components.

    Defines how context window should be allocated between
    system prompt, conversation history, tools, and response.

    All token counts are validated to be non-negative and
    within total budget constraints.
    """

    total: int
    system_prompt: int = 0
    conversation: int = 0
    tools: int = 0
    response_reserve: int = 4096

    def __post_init__(self) -> None:
        """Validate budget constraints."""
        if self.total <= 0:
            raise ValueError("total must be positive")
        if self.response_reserve < 0:
            raise ValueError("response_reserve cannot be negative")
        if self.response_reserve >= self.total:
            raise ValueError("response_reserve must be less than total")

        # Ensure all allocations are non-negative
        self.system_prompt = max(0, self.system_prompt)
        self.conversation = max(0, self.conversation)
        self.tools = max(0, self.tools)

    @property
    def available(self) -> int:
        """Available tokens for new content.

        Returns:
            Tokens available after allocations (never negative).
        """
        used = self.system_prompt + self.conversation + self.tools
        return max(0, self.total - used - self.response_reserve)

    @property
    def conversation_budget(self) -> int:
        """Budget available for conversation.

        Returns:
            Maximum tokens for conversation history (never negative).
        """
        budget = self.total - self.system_prompt - self.tools - self.response_reserve
        return max(0, budget)

    @property
    def is_over_budget(self) -> bool:
        """Check if allocations exceed total budget.

        Returns:
            True if allocations exceed available space.
        """
        used = (
            self.system_prompt + self.conversation + self.tools + self.response_reserve
        )
        return used > self.total

    def update_system_prompt(self, tokens: int) -> None:
        """Update system prompt token count."""
        self.system_prompt = max(0, tokens)

    def update_tools(self, tokens: int) -> None:
        """Update tools token count."""
        self.tools = max(0, tokens)

    def update_conversation(self, tokens: int) -> None:
        """Update conversation token count."""
        self.conversation = max(0, tokens)


# Known model context limits
MODEL_LIMITS: dict[str, tuple[int, int]] = {
    # Claude models (context, max_output)
    "claude-3-opus": (200_000, 4096),
    "claude-3-sonnet": (200_000, 4096),
    "claude-3-haiku": (200_000, 4096),
    "claude-3.5-sonnet": (200_000, 8192),
    "claude-2": (100_000, 4096),
    # GPT models
    "gpt-4-turbo": (128_000, 4096),
    "gpt-4-32k": (32_768, 4096),
    "gpt-4": (8_192, 4096),
    "gpt-3.5-turbo-16k": (16_385, 4096),
    "gpt-3.5-turbo": (4_096, 4096),
    # Llama models
    "llama-3-70b": (8_192, 4096),
    "llama-3-8b": (8_192, 4096),
    "llama-2-70b": (4_096, 4096),
    # Mistral models
    "mistral-large": (32_768, 4096),
    "mistral-medium": (32_768, 4096),
    "mistral-small": (32_768, 4096),
    "mixtral-8x7b": (32_768, 4096),
    # Default for unknown models
    "default": (8_192, 4096),
}


@dataclass
class ContextLimits:
    """Context window limits for a model.

    Defines the maximum context and output sizes for a model.
    """

    model: str
    max_tokens: int
    max_output_tokens: int
    reserved_tokens: int = 1000  # Buffer for safety

    @classmethod
    def for_model(cls, model: str) -> "ContextLimits":
        """Get context limits for a model.

        Args:
            model: Model name or identifier.

        Returns:
            ContextLimits for the model.
        """
        model_lower = model.lower()

        # Try exact match
        if model_lower in MODEL_LIMITS:
            max_ctx, max_out = MODEL_LIMITS[model_lower]
            return cls(model=model, max_tokens=max_ctx, max_output_tokens=max_out)

        # Try prefix match
        for key, (max_ctx, max_out) in MODEL_LIMITS.items():
            if key in model_lower or model_lower.startswith(key):
                return cls(model=model, max_tokens=max_ctx, max_output_tokens=max_out)

        # Default limits
        logger.warning(f"Unknown model {model}, using default limits")
        max_ctx, max_out = MODEL_LIMITS["default"]
        return cls(model=model, max_tokens=max_ctx, max_output_tokens=max_out)

    @property
    def effective_limit(self) -> int:
        """Effective context limit after reserves.

        Returns:
            Usable context tokens.
        """
        return self.max_tokens - self.max_output_tokens - self.reserved_tokens


@dataclass
class ContextTracker:
    """Tracks current context usage.

    Monitors token usage across messages and detects overflow.
    """

    limits: ContextLimits
    counter: TokenCounter
    budget: ContextBudget = field(init=False)

    # Current state
    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    tool_definitions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize budget with limits."""
        # Ensure response_reserve doesn't exceed available budget
        total = self.limits.effective_limit
        max_reserve = max(0, total - 1000)  # Leave at least 1000 for content
        response_reserve = min(self.limits.max_output_tokens, max_reserve)

        self.budget = ContextBudget(
            total=max(total, response_reserve + 1),  # Ensure total > reserve
            response_reserve=response_reserve,
        )

    @classmethod
    def for_model(cls, model: str) -> "ContextTracker":
        """Create tracker for a model.

        Args:
            model: Model name.

        Returns:
            ContextTracker instance.
        """
        limits = ContextLimits.for_model(model)
        counter = get_counter(model)
        return cls(limits=limits, counter=counter)

    def set_system_prompt(self, prompt: str) -> int:
        """Set system prompt and count tokens.

        Args:
            prompt: System prompt text.

        Returns:
            Token count for prompt.
        """
        self.system_prompt = prompt
        tokens = self.counter.count(prompt)
        self.budget.update_system_prompt(tokens)
        return tokens

    def set_tool_definitions(self, tools: list[dict[str, Any]]) -> int:
        """Set tool definitions and count tokens.

        Args:
            tools: Tool definition dictionaries.

        Returns:
            Token count for tools.
        """
        self.tool_definitions = tools
        # Estimate tool tokens
        tools_json = json.dumps(tools)
        tokens = self.counter.count(tools_json)
        self.budget.update_tools(tokens)
        return tokens

    def update(self, messages: list[dict[str, Any]]) -> int:
        """Update with new message list.

        Args:
            messages: Full message list.

        Returns:
            Token count for messages.
        """
        self.messages = list(messages)
        tokens = self.counter.count_messages(messages)
        self.budget.update_conversation(tokens)
        return tokens

    def add_message(self, message: dict[str, Any]) -> int:
        """Add a single message.

        Args:
            message: Message to add.

        Returns:
            Token count for message.
        """
        self.messages.append(message)
        tokens = self.counter.count_message(message)
        self.budget.conversation += tokens
        return tokens

    def current_tokens(self) -> int:
        """Get current total token usage.

        Returns:
            Total tokens in use.
        """
        return self.budget.system_prompt + self.budget.conversation + self.budget.tools

    def exceeds_limit(self) -> bool:
        """Check if context exceeds limit.

        Returns:
            True if over limit. Also returns True if conversation_budget is 0
            (no space for conversation) and there are conversation tokens.
        """
        budget = self.budget.conversation_budget
        # Edge case: if budget is 0, any conversation tokens exceed limit
        if budget <= 0:
            return self.budget.conversation > 0
        return self.current_tokens() > budget

    def overflow_amount(self) -> int:
        """Calculate how many tokens over limit.

        Returns:
            Tokens over limit (0 if under).
        """
        diff = self.current_tokens() - self.budget.conversation_budget
        return max(0, diff)

    def available_tokens(self) -> int:
        """Get available tokens for new content.

        Returns:
            Available tokens.
        """
        return self.budget.available

    def usage_percentage(self) -> float:
        """Get context usage as percentage.

        Returns:
            Usage percentage (0-100).
        """
        if self.limits.effective_limit == 0:
            return 100.0
        return (self.current_tokens() / self.limits.effective_limit) * 100

    def reset(self) -> None:
        """Reset all messages."""
        self.messages = []
        self.budget.update_conversation(0)
