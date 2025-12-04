"""Tests for mode base classes."""

import pytest

from opencode.modes.base import (
    Mode,
    ModeConfig,
    ModeContext,
    ModeName,
    ModeState,
    NormalMode,
)


class TestModeName:
    """Tests for ModeName enum."""

    def test_normal_value(self) -> None:
        """Test NORMAL mode has correct value."""
        assert ModeName.NORMAL.value == "normal"

    def test_plan_value(self) -> None:
        """Test PLAN mode has correct value."""
        assert ModeName.PLAN.value == "plan"

    def test_thinking_value(self) -> None:
        """Test THINKING mode has correct value."""
        assert ModeName.THINKING.value == "thinking"

    def test_headless_value(self) -> None:
        """Test HEADLESS mode has correct value."""
        assert ModeName.HEADLESS.value == "headless"

    def test_all_modes_exist(self) -> None:
        """Test all expected modes exist."""
        modes = [m.value for m in ModeName]
        assert "normal" in modes
        assert "plan" in modes
        assert "thinking" in modes
        assert "headless" in modes


class TestModeConfig:
    """Tests for ModeConfig dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic config creation."""
        config = ModeConfig(
            name=ModeName.NORMAL,
            description="Test mode",
        )
        assert config.name == ModeName.NORMAL
        assert config.description == "Test mode"
        assert config.system_prompt_addition == ""
        assert config.enabled is True
        assert config.settings == {}

    def test_with_prompt_addition(self) -> None:
        """Test config with prompt addition."""
        config = ModeConfig(
            name=ModeName.PLAN,
            description="Plan mode",
            system_prompt_addition="Extra instructions",
        )
        assert config.system_prompt_addition == "Extra instructions"

    def test_disabled_config(self) -> None:
        """Test disabled config."""
        config = ModeConfig(
            name=ModeName.NORMAL,
            description="Disabled",
            enabled=False,
        )
        assert config.enabled is False

    def test_get_setting_exists(self) -> None:
        """Test getting existing setting."""
        config = ModeConfig(
            name=ModeName.NORMAL,
            description="Test",
            settings={"key": "value"},
        )
        assert config.get_setting("key") == "value"

    def test_get_setting_not_exists(self) -> None:
        """Test getting non-existent setting returns None."""
        config = ModeConfig(name=ModeName.NORMAL, description="Test")
        assert config.get_setting("missing") is None

    def test_get_setting_with_default(self) -> None:
        """Test getting non-existent setting with default."""
        config = ModeConfig(name=ModeName.NORMAL, description="Test")
        assert config.get_setting("missing", "default") == "default"

    def test_set_setting(self) -> None:
        """Test setting a setting."""
        config = ModeConfig(name=ModeName.NORMAL, description="Test")
        config.set_setting("key", "value")
        assert config.settings["key"] == "value"


class TestModeContext:
    """Tests for ModeContext dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic context creation."""
        context = ModeContext()
        assert context.session is None
        assert context.config is None
        assert context.data == {}

    def test_with_session(self) -> None:
        """Test context with session."""
        session = {"id": "test"}
        context = ModeContext(session=session)
        assert context.session == session

    def test_with_output_handler(self) -> None:
        """Test context with output handler."""
        messages: list[str] = []

        def handler(msg: str) -> None:
            messages.append(msg)

        context = ModeContext(output=handler)
        context.output("Test message")
        assert messages == ["Test message"]

    def test_get_data_exists(self) -> None:
        """Test getting existing data."""
        context = ModeContext(data={"key": "value"})
        assert context.get("key") == "value"

    def test_get_data_not_exists(self) -> None:
        """Test getting non-existent data."""
        context = ModeContext()
        assert context.get("missing") is None

    def test_get_data_with_default(self) -> None:
        """Test getting data with default."""
        context = ModeContext()
        assert context.get("missing", "default") == "default"

    def test_set_data(self) -> None:
        """Test setting data."""
        context = ModeContext()
        context.set("key", "value")
        assert context.data["key"] == "value"


class TestModeState:
    """Tests for ModeState dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic state creation."""
        state = ModeState(mode_name=ModeName.NORMAL)
        assert state.mode_name == ModeName.NORMAL
        assert state.active is False
        assert state.data == {}

    def test_active_state(self) -> None:
        """Test active state."""
        state = ModeState(mode_name=ModeName.PLAN, active=True)
        assert state.active is True

    def test_with_data(self) -> None:
        """Test state with data."""
        state = ModeState(
            mode_name=ModeName.PLAN,
            data={"plan": {"title": "Test"}},
        )
        assert state.data["plan"]["title"] == "Test"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        state = ModeState(
            mode_name=ModeName.PLAN,
            active=True,
            data={"key": "value"},
        )
        result = state.to_dict()
        assert result == {
            "mode_name": "plan",
            "active": True,
            "data": {"key": "value"},
        }

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "mode_name": "thinking",
            "active": True,
            "data": {"key": "value"},
        }
        state = ModeState.from_dict(data)
        assert state.mode_name == ModeName.THINKING
        assert state.active is True
        assert state.data == {"key": "value"}

    def test_from_dict_minimal(self) -> None:
        """Test deserialization with minimal data."""
        data = {"mode_name": "normal"}
        state = ModeState.from_dict(data)
        assert state.mode_name == ModeName.NORMAL
        assert state.active is False
        assert state.data == {}

    def test_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = ModeState(
            mode_name=ModeName.HEADLESS,
            active=True,
            data={"nested": {"value": 42}},
        )
        restored = ModeState.from_dict(original.to_dict())
        assert restored.mode_name == original.mode_name
        assert restored.active == original.active
        assert restored.data == original.data


class TestNormalMode:
    """Tests for NormalMode class."""

    def test_name(self) -> None:
        """Test mode name."""
        mode = NormalMode()
        assert mode.name == ModeName.NORMAL

    def test_default_config(self) -> None:
        """Test default configuration."""
        mode = NormalMode()
        assert mode.config.name == ModeName.NORMAL
        assert mode.config.description == "Normal operating mode"
        assert mode.config.system_prompt_addition == ""

    def test_initial_state(self) -> None:
        """Test initial state."""
        mode = NormalMode()
        assert mode.is_active is False
        assert mode.state.mode_name == ModeName.NORMAL

    def test_activate(self) -> None:
        """Test mode activation."""
        mode = NormalMode()
        messages: list[str] = []
        context = ModeContext(output=lambda m: messages.append(m))

        mode.activate(context)

        assert mode.is_active is True
        assert "normal mode" in messages[0].lower()

    def test_deactivate(self) -> None:
        """Test mode deactivation."""
        mode = NormalMode()
        context = ModeContext(output=lambda m: None)

        mode.activate(context)
        mode.deactivate(context)

        assert mode.is_active is False

    def test_modify_prompt_unchanged(self) -> None:
        """Test that normal mode doesn't modify prompt."""
        mode = NormalMode()
        base = "You are a helpful assistant."
        result = mode.modify_prompt(base)
        assert result == base

    def test_modify_response_unchanged(self) -> None:
        """Test that normal mode doesn't modify response."""
        mode = NormalMode()
        response = "Here is my response."
        result = mode.modify_response(response)
        assert result == response

    def test_should_not_auto_activate(self) -> None:
        """Test that normal mode doesn't auto-activate."""
        mode = NormalMode()
        assert mode.should_auto_activate("any message") is False

    def test_save_and_restore_state(self) -> None:
        """Test state persistence."""
        mode = NormalMode()
        context = ModeContext(output=lambda m: None)
        mode.activate(context)

        saved = mode.save_state()
        mode.deactivate(context)

        new_mode = NormalMode()
        new_mode.restore_state(saved)

        assert new_mode.state.active is True
        assert new_mode.state.mode_name == ModeName.NORMAL


class TestModeWithCustomConfig:
    """Tests for Mode base class with custom config."""

    def test_custom_config_override(self) -> None:
        """Test custom config overrides defaults."""
        custom_config = ModeConfig(
            name=ModeName.NORMAL,
            description="Custom description",
            system_prompt_addition="Custom addition",
            enabled=False,
        )
        mode = NormalMode(config=custom_config)

        assert mode.config.description == "Custom description"
        assert mode.config.system_prompt_addition == "Custom addition"
        assert mode.config.enabled is False

    def test_prompt_modification_with_addition(self) -> None:
        """Test prompt modification with custom addition."""
        custom_config = ModeConfig(
            name=ModeName.NORMAL,
            description="Test",
            system_prompt_addition="Extra instructions.",
        )
        mode = NormalMode(config=custom_config)

        base = "You are helpful."
        result = mode.modify_prompt(base)

        assert "You are helpful." in result
        assert "Extra instructions." in result
