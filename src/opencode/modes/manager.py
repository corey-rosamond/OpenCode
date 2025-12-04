"""
Mode manager for operating modes.

Handles mode registration, switching, and state management.
Provides the central coordination point for mode operations.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

from .base import Mode, ModeContext, ModeName, NormalMode

logger = logging.getLogger(__name__)


class ModeError(Exception):
    """Base exception for mode errors."""

    pass


class ModeNotFoundError(ModeError):
    """Raised when requested mode doesn't exist."""

    pass


class ModeSwitchError(ModeError):
    """Raised when mode switch fails."""

    pass


class ModeManager:
    """Manages operating modes.

    Singleton that tracks registered modes and the current
    active mode. Handles mode switching and state persistence.

    Thread-safe implementation using locks for all mutations.
    """

    _instance: "ModeManager | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ModeManager":
        """Create singleton instance.

        Returns:
            The singleton ModeManager instance
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize mode manager with normal mode."""
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._modes: dict[ModeName, Mode] = {}
        self._current_mode: ModeName = ModeName.NORMAL
        self._mode_stack: list[ModeName] = []
        self._on_mode_change: list[Callable[[ModeName, ModeName], None]] = []

        # Register default normal mode
        self._modes[ModeName.NORMAL] = NormalMode()

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ModeManager":
        """Get singleton instance.

        Returns:
            The singleton ModeManager instance
        """
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._instance_lock:
            cls._instance = None

    def register_mode(self, mode: Mode) -> None:
        """Register an operating mode.

        Args:
            mode: Mode instance to register

        Raises:
            ValueError: If mode with same name already registered
        """
        with self._lock:
            if mode.name in self._modes:
                raise ValueError(f"Mode already registered: {mode.name.value}")
            self._modes[mode.name] = mode
            logger.debug(f"Registered mode: {mode.name.value}")

    def unregister_mode(self, name: ModeName) -> bool:
        """Unregister a mode.

        Args:
            name: Name of mode to unregister

        Returns:
            True if mode was unregistered, False if not found
        """
        with self._lock:
            if name == ModeName.NORMAL:
                logger.warning("Cannot unregister normal mode")
                return False
            if name in self._modes:
                del self._modes[name]
                logger.debug(f"Unregistered mode: {name.value}")
                return True
            return False

    def get_mode(self, name: ModeName) -> Mode | None:
        """Get mode by name.

        Args:
            name: Mode name to look up

        Returns:
            Mode instance or None if not found
        """
        with self._lock:
            return self._modes.get(name)

    def get_current_mode(self) -> Mode:
        """Get currently active mode.

        Returns:
            The currently active Mode instance
        """
        with self._lock:
            return self._modes[self._current_mode]

    @property
    def current_mode_name(self) -> ModeName:
        """Get current mode name.

        Returns:
            The ModeName of the current mode
        """
        with self._lock:
            return self._current_mode

    def list_modes(self) -> list[Mode]:
        """List all registered modes.

        Returns:
            List of all registered Mode instances
        """
        with self._lock:
            return list(self._modes.values())

    def list_enabled_modes(self) -> list[Mode]:
        """List only enabled modes.

        Returns:
            List of enabled Mode instances
        """
        with self._lock:
            return [m for m in self._modes.values() if m.config.enabled]

    def switch_mode(
        self,
        name: ModeName,
        context: ModeContext,
        push: bool = False,
    ) -> bool:
        """Switch to specified mode.

        Args:
            name: Target mode name
            context: Mode context
            push: If True, push current mode to stack

        Returns:
            True if switch successful

        Raises:
            ModeNotFoundError: If mode not found
            ModeSwitchError: If switch fails
        """
        with self._lock:
            if name not in self._modes:
                raise ModeNotFoundError(f"Mode not found: {name.value}")

            if not self._modes[name].config.enabled:
                raise ModeSwitchError(f"Mode is disabled: {name.value}")

            old_mode = self._current_mode

            try:
                # Deactivate current mode
                self._modes[old_mode].deactivate(context)

                # Push to stack if requested
                if push:
                    self._mode_stack.append(old_mode)

                # Activate new mode
                self._modes[name].activate(context)
                self._current_mode = name

                # Notify listeners (outside lock would be better but simpler this way)
                for callback in self._on_mode_change:
                    try:
                        callback(old_mode, name)
                    except Exception as e:
                        logger.warning(f"Mode change callback failed: {e}")

                logger.info(f"Switched mode: {old_mode.value} -> {name.value}")
                return True

            except Exception as e:
                logger.error(f"Mode switch failed: {e}")
                # Try to restore old mode
                try:
                    self._modes[old_mode].activate(context)
                    self._current_mode = old_mode
                except Exception:
                    pass
                raise ModeSwitchError(f"Failed to switch to {name.value}: {e}") from e

    def pop_mode(self, context: ModeContext) -> ModeName | None:
        """Pop previous mode from stack.

        Args:
            context: Mode context

        Returns:
            Previous mode name, or None if stack empty
        """
        with self._lock:
            if not self._mode_stack:
                return None

            previous = self._mode_stack.pop()
            self.switch_mode(previous, context)
            return previous

    def reset_mode(self, context: ModeContext) -> None:
        """Reset to normal mode, clearing stack.

        Args:
            context: Mode context
        """
        with self._lock:
            self._mode_stack.clear()
            if self._current_mode != ModeName.NORMAL:
                self.switch_mode(ModeName.NORMAL, context)

    def get_system_prompt(self, base_prompt: str) -> str:
        """Get prompt modified by current mode.

        Args:
            base_prompt: Base system prompt

        Returns:
            Modified prompt
        """
        with self._lock:
            current = self.get_current_mode()
            return current.modify_prompt(base_prompt)

    def process_response(self, response: str) -> str:
        """Process response through current mode.

        Args:
            response: Raw response text

        Returns:
            Processed response
        """
        with self._lock:
            current = self.get_current_mode()
            return current.modify_response(response)

    def check_auto_activation(self, message: str) -> ModeName | None:
        """Check if any mode should auto-activate.

        Args:
            message: User message

        Returns:
            Mode name if auto-activation triggered, None otherwise
        """
        with self._lock:
            for mode in self._modes.values():
                if (
                    mode.name != self._current_mode
                    and mode.config.enabled
                    and mode.should_auto_activate(message)
                ):
                    return mode.name
            return None

    def on_mode_change(
        self,
        callback: Callable[[ModeName, ModeName], None],
    ) -> None:
        """Register callback for mode changes.

        Callback receives (old_mode, new_mode).

        Args:
            callback: Function to call on mode change
        """
        with self._lock:
            self._on_mode_change.append(callback)

    def save_state(self) -> dict[str, Any]:
        """Save mode manager state for persistence.

        Returns:
            Dictionary containing serialized state
        """
        with self._lock:
            return {
                "current_mode": self._current_mode.value,
                "mode_stack": [m.value for m in self._mode_stack],
                "mode_states": {
                    name.value: mode.save_state()
                    for name, mode in self._modes.items()
                },
            }

    def restore_state(self, data: dict[str, Any], context: ModeContext) -> None:
        """Restore mode manager state from persisted data.

        Args:
            data: Dictionary containing serialized state
            context: Mode context for activation
        """
        with self._lock:
            # Restore mode-specific states
            mode_states = data.get("mode_states", {})
            for name_str, state in mode_states.items():
                try:
                    name = ModeName(name_str)
                    if name in self._modes:
                        self._modes[name].restore_state(state)
                except ValueError:
                    logger.warning(f"Unknown mode in state: {name_str}")

            # Restore stack
            self._mode_stack = []
            for m in data.get("mode_stack", []):
                try:
                    self._mode_stack.append(ModeName(m))
                except ValueError:
                    logger.warning(f"Unknown mode in stack: {m}")

            # Restore current mode
            current = data.get("current_mode", "normal")
            try:
                target_mode = ModeName(current)
                if target_mode in self._modes and target_mode != self._current_mode:
                    # Activate the target mode
                    self._modes[self._current_mode].deactivate(context)
                    self._modes[target_mode].activate(context)
                    self._current_mode = target_mode
            except ValueError:
                logger.warning(f"Unknown current mode: {current}")
