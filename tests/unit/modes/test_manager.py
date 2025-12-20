"""Tests for ModeManager."""

import pytest

from code_forge.modes.base import Mode, ModeConfig, ModeContext, ModeName, NormalMode
from code_forge.modes.manager import (
    ModeError,
    ModeManager,
    ModeNotFoundError,
    ModeSwitchError,
)
from code_forge.modes.plan import PlanMode
from code_forge.modes.thinking import ThinkingMode


@pytest.fixture
def manager() -> ModeManager:
    """Create fresh manager for each test."""
    ModeManager.reset_instance()
    return ModeManager.get_instance()


@pytest.fixture
def context() -> ModeContext:
    """Create test context."""
    messages: list[str] = []
    return ModeContext(output=lambda m: messages.append(m))


class TestModeManagerSingleton:
    """Tests for singleton behavior."""

    def test_get_instance_returns_same(self) -> None:
        """Test get_instance returns same instance."""
        ModeManager.reset_instance()
        m1 = ModeManager.get_instance()
        m2 = ModeManager.get_instance()
        assert m1 is m2

    def test_direct_instantiation_same(self) -> None:
        """Test direct instantiation returns same instance."""
        ModeManager.reset_instance()
        m1 = ModeManager()
        m2 = ModeManager()
        assert m1 is m2

    def test_reset_instance(self) -> None:
        """Test reset creates new instance."""
        ModeManager.reset_instance()
        m1 = ModeManager.get_instance()
        ModeManager.reset_instance()
        m2 = ModeManager.get_instance()
        assert m1 is not m2


class TestModeRegistration:
    """Tests for mode registration."""

    def test_normal_mode_registered_by_default(self, manager: ModeManager) -> None:
        """Test NormalMode is registered by default."""
        mode = manager.get_mode(ModeName.NORMAL)
        assert isinstance(mode, NormalMode)

    def test_register_mode(self, manager: ModeManager) -> None:
        """Test registering a new mode."""
        plan_mode = PlanMode()
        manager.register_mode(plan_mode)

        mode = manager.get_mode(ModeName.PLAN)
        assert isinstance(mode, PlanMode)

    def test_register_duplicate_raises(self, manager: ModeManager) -> None:
        """Test registering duplicate mode raises error."""
        manager.register_mode(PlanMode())

        with pytest.raises(ValueError, match="already registered"):
            manager.register_mode(PlanMode())

    def test_unregister_mode(self, manager: ModeManager) -> None:
        """Test unregistering a mode."""
        manager.register_mode(PlanMode())
        result = manager.unregister_mode(ModeName.PLAN)

        assert result is True
        assert manager.get_mode(ModeName.PLAN) is None

    def test_unregister_nonexistent(self, manager: ModeManager) -> None:
        """Test unregistering non-existent mode returns False."""
        result = manager.unregister_mode(ModeName.PLAN)
        assert result is False

    def test_cannot_unregister_normal(self, manager: ModeManager) -> None:
        """Test cannot unregister normal mode."""
        result = manager.unregister_mode(ModeName.NORMAL)
        assert result is False
        assert isinstance(manager.get_mode(ModeName.NORMAL), Mode)


class TestModeQueries:
    """Tests for mode query methods."""

    def test_get_current_mode_default(self, manager: ModeManager) -> None:
        """Test default current mode is normal."""
        current = manager.get_current_mode()
        assert isinstance(current, NormalMode)

    def test_current_mode_name(self, manager: ModeManager) -> None:
        """Test current mode name property."""
        assert manager.current_mode_name == ModeName.NORMAL

    def test_list_modes(self, manager: ModeManager) -> None:
        """Test listing all modes."""
        manager.register_mode(PlanMode())
        manager.register_mode(ThinkingMode())

        modes = manager.list_modes()
        assert len(modes) == 3  # Normal + Plan + Thinking

    def test_list_enabled_modes(self, manager: ModeManager) -> None:
        """Test listing enabled modes only."""
        plan_mode = PlanMode()
        plan_mode._config = ModeConfig(
            name=ModeName.PLAN,
            description="Disabled",
            enabled=False,
        )
        manager.register_mode(plan_mode)
        manager.register_mode(ThinkingMode())

        enabled = manager.list_enabled_modes()
        names = [m.name for m in enabled]

        assert ModeName.NORMAL in names
        assert ModeName.THINKING in names
        assert ModeName.PLAN not in names


class TestModeSwitching:
    """Tests for mode switching."""

    def test_switch_mode_success(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test successful mode switch."""
        manager.register_mode(PlanMode())

        result = manager.switch_mode(ModeName.PLAN, context)

        assert result is True
        assert manager.current_mode_name == ModeName.PLAN
        assert manager.get_current_mode().is_active is True

    def test_switch_mode_not_found(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test switching to non-existent mode."""
        with pytest.raises(ModeNotFoundError):
            manager.switch_mode(ModeName.PLAN, context)

    def test_switch_mode_disabled(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test switching to disabled mode."""
        plan_mode = PlanMode()
        plan_mode._config = ModeConfig(
            name=ModeName.PLAN,
            description="Disabled",
            enabled=False,
        )
        manager.register_mode(plan_mode)

        with pytest.raises(ModeSwitchError, match="disabled"):
            manager.switch_mode(ModeName.PLAN, context)

    def test_switch_deactivates_old_mode(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test switch deactivates old mode."""
        manager.register_mode(PlanMode())

        # Activate normal mode explicitly
        normal = manager.get_mode(ModeName.NORMAL)
        assert isinstance(normal, Mode)
        normal.activate(context)
        assert normal.is_active is True

        # Switch to plan mode
        manager.switch_mode(ModeName.PLAN, context)

        # Normal should be deactivated
        assert normal.is_active is False

    def test_switch_with_push(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test switch with push to stack."""
        manager.register_mode(PlanMode())

        manager.switch_mode(ModeName.PLAN, context, push=True)

        assert manager.current_mode_name == ModeName.PLAN
        # Stack should have NORMAL

    def test_pop_mode(self, manager: ModeManager, context: ModeContext) -> None:
        """Test popping mode from stack."""
        manager.register_mode(PlanMode())

        manager.switch_mode(ModeName.PLAN, context, push=True)
        previous = manager.pop_mode(context)

        assert previous == ModeName.NORMAL
        assert manager.current_mode_name == ModeName.NORMAL

    def test_pop_empty_stack(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test popping from empty stack returns None."""
        result = manager.pop_mode(context)
        assert result is None

    def test_reset_mode(self, manager: ModeManager, context: ModeContext) -> None:
        """Test reset to normal mode."""
        manager.register_mode(PlanMode())
        manager.switch_mode(ModeName.PLAN, context, push=True)

        manager.reset_mode(context)

        assert manager.current_mode_name == ModeName.NORMAL


class TestPromptAndResponse:
    """Tests for prompt and response processing."""

    def test_get_system_prompt_normal(self, manager: ModeManager) -> None:
        """Test getting prompt in normal mode."""
        base = "You are helpful."
        result = manager.get_system_prompt(base)
        assert result == base

    def test_get_system_prompt_with_addition(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test getting prompt with mode addition."""
        manager.register_mode(PlanMode())
        manager.switch_mode(ModeName.PLAN, context)

        base = "You are helpful."
        result = manager.get_system_prompt(base)

        assert "You are helpful." in result
        assert "PLAN MODE" in result

    def test_process_response_passthrough(self, manager: ModeManager) -> None:
        """Test response passthrough in normal mode."""
        response = "Here is my response."
        result = manager.process_response(response)
        assert result == response


class TestAutoActivation:
    """Tests for auto-activation."""

    def test_check_auto_activation_none(self, manager: ModeManager) -> None:
        """Test no auto-activation for normal message."""
        result = manager.check_auto_activation("Hello world")
        assert result is None

    def test_check_auto_activation_plan(self, manager: ModeManager) -> None:
        """Test auto-activation for planning request."""
        manager.register_mode(PlanMode())

        result = manager.check_auto_activation("Plan how to add authentication")
        assert result == ModeName.PLAN

    def test_no_auto_activation_if_already_active(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test no auto-activation if already in that mode."""
        manager.register_mode(PlanMode())
        manager.switch_mode(ModeName.PLAN, context)

        result = manager.check_auto_activation("Plan how to add authentication")
        assert result is None


class TestModeChangeCallback:
    """Tests for mode change callbacks."""

    def test_callback_called_on_switch(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test callback is called on mode switch."""
        manager.register_mode(PlanMode())
        calls: list[tuple[ModeName, ModeName]] = []

        def callback(old: ModeName, new: ModeName) -> None:
            calls.append((old, new))

        manager.on_mode_change(callback)
        manager.switch_mode(ModeName.PLAN, context)

        assert len(calls) == 1
        assert calls[0] == (ModeName.NORMAL, ModeName.PLAN)

    def test_multiple_callbacks(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test multiple callbacks are called."""
        manager.register_mode(PlanMode())
        calls1: list[tuple[ModeName, ModeName]] = []
        calls2: list[tuple[ModeName, ModeName]] = []

        manager.on_mode_change(lambda o, n: calls1.append((o, n)))
        manager.on_mode_change(lambda o, n: calls2.append((o, n)))
        manager.switch_mode(ModeName.PLAN, context)

        assert len(calls1) == 1
        assert len(calls2) == 1


class TestStatePersistence:
    """Tests for state persistence."""

    def test_save_state(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test saving state."""
        manager.register_mode(PlanMode())
        manager.switch_mode(ModeName.PLAN, context, push=True)

        state = manager.save_state()

        assert state["current_mode"] == "plan"
        assert "normal" in state["mode_stack"]
        assert "plan" in state["mode_states"]

    def test_restore_state(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test restoring state."""
        manager.register_mode(PlanMode())

        state = {
            "current_mode": "plan",
            "mode_stack": ["normal"],
            "mode_states": {
                "normal": {"mode_name": "normal", "active": False, "data": {}},
                "plan": {"mode_name": "plan", "active": True, "data": {}},
            },
        }

        manager.restore_state(state, context)

        assert manager.current_mode_name == ModeName.PLAN

    def test_restore_state_with_unknown_mode(
        self, manager: ModeManager, context: ModeContext
    ) -> None:
        """Test restoring state with unknown mode in stack."""
        state = {
            "current_mode": "normal",
            "mode_stack": ["unknown_mode"],
            "mode_states": {},
        }

        # Should not raise, just log warning
        manager.restore_state(state, context)
        assert manager.current_mode_name == ModeName.NORMAL
