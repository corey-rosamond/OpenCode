"""Model routing and variants for OpenRouter."""

from enum import Enum


class RouteVariant(str, Enum):
    """OpenRouter routing variants."""

    DEFAULT = ""
    NITRO = ":nitro"  # Fastest providers
    FLOOR = ":floor"  # Cheapest providers
    ONLINE = ":online"  # Web search enabled
    THINKING = ":thinking"  # Extended reasoning (Claude)


def apply_variant(model_id: str, variant: RouteVariant) -> str:
    """
    Apply routing variant to model ID.

    Args:
        model_id: Base model ID (e.g., "anthropic/claude-3-opus")
        variant: Routing variant to apply

    Returns:
        Model ID with variant suffix

    Example:
        apply_variant("anthropic/claude-3-opus", RouteVariant.NITRO)
        # Returns: "anthropic/claude-3-opus:nitro"
    """
    if variant == RouteVariant.DEFAULT or not variant.value:
        return model_id
    return f"{model_id}{variant.value}"


def parse_model_id(model_id: str) -> tuple[str, RouteVariant | None]:
    """
    Parse model ID to extract base model and variant.

    Args:
        model_id: Model ID potentially with variant

    Returns:
        Tuple of (base_model_id, variant or None)

    Example:
        parse_model_id("anthropic/claude-3-opus:nitro")
        # Returns: ("anthropic/claude-3-opus", RouteVariant.NITRO)
    """
    for variant in RouteVariant:
        if variant.value and model_id.endswith(variant.value):
            base = model_id[: -len(variant.value)]
            return base, variant
    return model_id, None


# Common model aliases
MODEL_ALIASES: dict[str, str] = {
    # Claude models
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-sonnet": "anthropic/claude-3-sonnet",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3.5-haiku": "anthropic/claude-3.5-haiku",
    "claude-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-haiku": "anthropic/claude-3.5-haiku",
    "claude-opus": "anthropic/claude-3-opus",
    # OpenAI models
    "gpt-4": "openai/gpt-4",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "o1": "openai/o1",
    "o1-mini": "openai/o1-mini",
    "o1-preview": "openai/o1-preview",
    # Google models
    "gemini-pro": "google/gemini-pro",
    "gemini-pro-1.5": "google/gemini-pro-1.5",
    "gemini-flash": "google/gemini-flash-1.5",
    "gemini-flash-1.5": "google/gemini-flash-1.5",
    # Open source models
    "llama-3-70b": "meta-llama/llama-3-70b-instruct",
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
    "mistral-large": "mistralai/mistral-large",
    "deepseek-v3": "deepseek/deepseek-chat",
    "qwen-72b": "qwen/qwen-2.5-72b-instruct",
    # Moonshot models
    "kimi-k2": "moonshotai/kimi-k2",
}


# Approximate context limits for common models (in tokens)
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    # Claude models
    "anthropic/claude-3-opus": 200000,
    "anthropic/claude-3-sonnet": 200000,
    "anthropic/claude-3-haiku": 200000,
    "anthropic/claude-3.5-sonnet": 200000,
    "anthropic/claude-3.5-haiku": 200000,
    # OpenAI models
    "openai/gpt-4": 8192,
    "openai/gpt-4-turbo": 128000,
    "openai/gpt-4o": 128000,
    "openai/gpt-4o-mini": 128000,
    "openai/gpt-3.5-turbo": 16385,
    "openai/o1": 200000,
    "openai/o1-mini": 128000,
    "openai/o1-preview": 128000,
    # Google models
    "google/gemini-pro": 32000,
    "google/gemini-pro-1.5": 1000000,
    "google/gemini-flash-1.5": 1000000,
    # Open source
    "meta-llama/llama-3-70b-instruct": 8192,
    "meta-llama/llama-3.1-70b-instruct": 128000,
    "meta-llama/llama-3.1-405b-instruct": 128000,
    "mistralai/mixtral-8x7b-instruct": 32000,
    "mistralai/mistral-large": 128000,
    "deepseek/deepseek-chat": 64000,
    "qwen/qwen-2.5-72b-instruct": 32000,
    # Moonshot models
    "moonshotai/kimi-k2": 128000,
}


def get_model_context_limit(model_id: str) -> int:
    """Get the context limit for a model.

    Args:
        model_id: Model ID (alias or full).

    Returns:
        Context limit in tokens (default: 128000).
    """
    resolved = resolve_model_alias(model_id)
    return MODEL_CONTEXT_LIMITS.get(resolved, 128000)


def resolve_model_alias(model_id: str) -> str:
    """
    Resolve model alias to full model ID.

    Args:
        model_id: Model ID or alias to resolve.

    Returns:
        Full model ID.

    Raises:
        ValueError: If model_id is empty or None.
    """
    if not model_id or not model_id.strip():
        raise ValueError("model_id cannot be empty or None")
    return MODEL_ALIASES.get(model_id, model_id)
