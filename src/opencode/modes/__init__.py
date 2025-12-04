"""
Operating modes package.

Provides different operating modes that modify assistant
behavior: Plan, Thinking, and Headless modes.
"""

import contextlib

from .base import (
    Mode,
    ModeConfig,
    ModeContext,
    ModeName,
    ModeState,
    NormalMode,
    OutputHandler,
)
from .headless import (
    HeadlessConfig,
    HeadlessMode,
    HeadlessResult,
    OutputFormat,
    create_headless_config_from_args,
)
from .manager import (
    ModeError,
    ModeManager,
    ModeNotFoundError,
    ModeSwitchError,
)
from .plan import (
    Plan,
    PlanMode,
    PlanStep,
)
from .prompts import (
    HEADLESS_MODE_PROMPT,
    MODE_PROMPTS,
    PLAN_MODE_PROMPT,
    THINKING_MODE_DEEP_PROMPT,
    THINKING_MODE_PROMPT,
    get_mode_prompt,
)
from .thinking import (
    ThinkingConfig,
    ThinkingMode,
    ThinkingResult,
    should_suggest_thinking,
)

__all__ = [
    "HEADLESS_MODE_PROMPT",
    "MODE_PROMPTS",
    "PLAN_MODE_PROMPT",
    "THINKING_MODE_DEEP_PROMPT",
    "THINKING_MODE_PROMPT",
    "HeadlessConfig",
    "HeadlessMode",
    "HeadlessResult",
    "Mode",
    "ModeConfig",
    "ModeContext",
    "ModeError",
    "ModeManager",
    "ModeName",
    "ModeNotFoundError",
    "ModeState",
    "ModeSwitchError",
    "NormalMode",
    "OutputFormat",
    "OutputHandler",
    "Plan",
    "PlanMode",
    "PlanStep",
    "ThinkingConfig",
    "ThinkingMode",
    "ThinkingResult",
    "create_headless_config_from_args",
    "get_mode_prompt",
    "setup_modes",
    "should_suggest_thinking",
]


def setup_modes(manager: ModeManager | None = None) -> ModeManager:
    """Set up all default modes.

    Registers PlanMode, ThinkingMode, and HeadlessMode with
    the mode manager. If no manager is provided, uses the
    singleton instance.

    Args:
        manager: Existing manager or None to use singleton

    Returns:
        Configured mode manager
    """
    if manager is None:
        manager = ModeManager.get_instance()

    # Register standard modes (only if not already registered)
    with contextlib.suppress(ValueError):
        manager.register_mode(PlanMode())

    with contextlib.suppress(ValueError):
        manager.register_mode(ThinkingMode())

    with contextlib.suppress(ValueError):
        manager.register_mode(HeadlessMode())

    return manager
