"""
Base classes for operating modes.

Provides the foundation for implementing different operating modes
that modify assistant behavior, prompts, and interaction patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ModeName(Enum):
    """Available operating modes."""

    NORMAL = "normal"
    PLAN = "plan"
    THINKING = "thinking"
    HEADLESS = "headless"


class OutputHandler(Protocol):
    """Protocol for output handling."""

    def __call__(self, message: str) -> None:
        """Output a message."""
        ...


def _default_output_handler(message: str) -> None:
    """Default no-op output handler."""
    pass


@dataclass
class ModeConfig:
    """Configuration for an operating mode.

    Attributes:
        name: Mode identifier
        description: Human-readable description
        system_prompt_addition: Text to append to system prompt
        enabled: Whether mode is available
        settings: Mode-specific settings
    """

    name: ModeName
    description: str
    system_prompt_addition: str = ""
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a mode setting by key.

        Args:
            key: Setting key to retrieve
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set a mode setting.

        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value


@dataclass
class ModeContext:
    """Context provided to mode operations.

    Attributes:
        session: Current session object
        config: Application configuration
        output: Output handler function
        data: Additional context data
    """

    session: Any = None
    config: Any = None
    output: OutputHandler = field(default=_default_output_handler)
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get context data by key.

        Args:
            key: Data key to retrieve
            default: Default value if key not found

        Returns:
            Data value or default
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set context data.

        Args:
            key: Data key
            value: Data value
        """
        self.data[key] = value


@dataclass
class ModeState:
    """Persistent state for a mode.

    Stored in session for persistence across interactions.

    Attributes:
        mode_name: Name of the mode this state belongs to
        active: Whether the mode is currently active
        data: Mode-specific state data
    """

    mode_name: ModeName
    active: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of state
        """
        return {
            "mode_name": self.mode_name.value,
            "active": self.active,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModeState":
        """Deserialize from dictionary.

        Args:
            data: Dictionary to deserialize from

        Returns:
            ModeState instance
        """
        return cls(
            mode_name=ModeName(data["mode_name"]),
            active=data.get("active", False),
            data=data.get("data", {}),
        )


class Mode(ABC):
    """Abstract base class for operating modes.

    Modes modify assistant behavior through:
    - System prompt additions
    - Response post-processing
    - Custom activation/deactivation logic

    Subclasses must implement:
    - name property
    - _default_config() method
    - activate() method
    - deactivate() method
    """

    def __init__(self, config: ModeConfig | None = None) -> None:
        """Initialize mode with optional configuration.

        Args:
            config: Mode configuration, or None to use defaults
        """
        self._config = config or self._default_config()
        self._state = ModeState(mode_name=self.name)

    @property
    @abstractmethod
    def name(self) -> ModeName:
        """Return mode name.

        Returns:
            The ModeName enum value for this mode
        """
        ...

    @property
    def config(self) -> ModeConfig:
        """Return mode configuration.

        Returns:
            The ModeConfig for this mode
        """
        return self._config

    @property
    def state(self) -> ModeState:
        """Return mode state.

        Returns:
            The ModeState for this mode
        """
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if mode is currently active.

        Returns:
            True if mode is active, False otherwise
        """
        return self._state.active

    @abstractmethod
    def _default_config(self) -> ModeConfig:
        """Return default configuration for this mode.

        Returns:
            Default ModeConfig for this mode
        """
        ...

    @abstractmethod
    def activate(self, context: ModeContext) -> None:
        """Called when mode is activated.

        Override to perform setup when entering mode.
        Must call super().activate(context) to set state.

        Args:
            context: Mode context with session, config, output handler
        """
        self._state.active = True

    @abstractmethod
    def deactivate(self, context: ModeContext) -> None:
        """Called when mode is deactivated.

        Override to perform cleanup when leaving mode.
        Must call super().deactivate(context) to clear state.

        Args:
            context: Mode context with session, config, output handler
        """
        self._state.active = False
        self._state.data.clear()

    def modify_prompt(self, base_prompt: str) -> str:
        """Modify system prompt for this mode.

        Default implementation appends the prompt addition.
        Override for custom prompt modification.

        Args:
            base_prompt: The base system prompt

        Returns:
            Modified prompt with mode-specific additions
        """
        if self._config.system_prompt_addition:
            return f"{base_prompt}\n\n{self._config.system_prompt_addition}"
        return base_prompt

    def modify_response(self, response: str) -> str:
        """Post-process response for this mode.

        Default implementation returns response unchanged.
        Override for custom response processing.

        Args:
            response: The raw response text

        Returns:
            Processed response text
        """
        return response

    def should_auto_activate(self, message: str) -> bool:  # noqa: ARG002
        """Check if mode should auto-activate for given message.

        Default returns False. Override to enable auto-activation.

        Args:
            message: User message to check

        Returns:
            True if mode should auto-activate, False otherwise
        """
        return False

    def save_state(self) -> dict[str, Any]:
        """Save mode state for persistence.

        Returns:
            Dictionary containing serialized state
        """
        return self._state.to_dict()

    def restore_state(self, data: dict[str, Any]) -> None:
        """Restore mode state from persisted data.

        Args:
            data: Dictionary containing serialized state
        """
        self._state = ModeState.from_dict(data)


class NormalMode(Mode):
    """Default operating mode with no modifications.

    This is the base mode that returns prompts and responses unchanged.
    """

    @property
    def name(self) -> ModeName:
        """Return mode name.

        Returns:
            ModeName.NORMAL
        """
        return ModeName.NORMAL

    def _default_config(self) -> ModeConfig:
        """Return default configuration for normal mode.

        Returns:
            ModeConfig with no prompt additions
        """
        return ModeConfig(
            name=ModeName.NORMAL,
            description="Normal operating mode",
            system_prompt_addition="",
        )

    def activate(self, context: ModeContext) -> None:
        """Activate normal mode.

        Args:
            context: Mode context
        """
        super().activate(context)
        context.output("Returned to normal mode.")

    def deactivate(self, context: ModeContext) -> None:
        """Deactivate normal mode.

        Args:
            context: Mode context
        """
        super().deactivate(context)
