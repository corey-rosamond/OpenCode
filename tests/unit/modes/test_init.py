"""Tests for modes package initialization."""

import pytest

from opencode.modes import (
    HeadlessMode,
    Mode,
    ModeConfig,
    ModeContext,
    ModeManager,
    ModeName,
    ModeState,
    NormalMode,
    PlanMode,
    ThinkingMode,
    setup_modes,
)


class TestPackageExports:
    """Tests for package exports."""

    def test_mode_exported(self) -> None:
        """Test Mode class is exported."""
        assert Mode is not None

    def test_mode_config_exported(self) -> None:
        """Test ModeConfig class is exported."""
        assert ModeConfig is not None

    def test_mode_context_exported(self) -> None:
        """Test ModeContext class is exported."""
        assert ModeContext is not None

    def test_mode_name_exported(self) -> None:
        """Test ModeName enum is exported."""
        assert ModeName is not None
        assert ModeName.NORMAL is not None

    def test_mode_state_exported(self) -> None:
        """Test ModeState class is exported."""
        assert ModeState is not None

    def test_normal_mode_exported(self) -> None:
        """Test NormalMode class is exported."""
        assert NormalMode is not None

    def test_mode_manager_exported(self) -> None:
        """Test ModeManager class is exported."""
        assert ModeManager is not None

    def test_plan_mode_exported(self) -> None:
        """Test PlanMode class is exported."""
        assert PlanMode is not None

    def test_thinking_mode_exported(self) -> None:
        """Test ThinkingMode class is exported."""
        assert ThinkingMode is not None

    def test_headless_mode_exported(self) -> None:
        """Test HeadlessMode class is exported."""
        assert HeadlessMode is not None


class TestSetupModes:
    """Tests for setup_modes function."""

    @pytest.fixture(autouse=True)
    def reset_manager(self) -> None:
        """Reset ModeManager before each test."""
        ModeManager.reset_instance()
        yield
        ModeManager.reset_instance()

    def test_setup_modes_returns_manager(self) -> None:
        """Test setup_modes returns manager."""
        manager = setup_modes()
        assert isinstance(manager, ModeManager)

    def test_setup_modes_registers_plan(self) -> None:
        """Test setup_modes registers PlanMode."""
        manager = setup_modes()
        mode = manager.get_mode(ModeName.PLAN)
        assert mode is not None
        assert isinstance(mode, PlanMode)

    def test_setup_modes_registers_thinking(self) -> None:
        """Test setup_modes registers ThinkingMode."""
        manager = setup_modes()
        mode = manager.get_mode(ModeName.THINKING)
        assert mode is not None
        assert isinstance(mode, ThinkingMode)

    def test_setup_modes_registers_headless(self) -> None:
        """Test setup_modes registers HeadlessMode."""
        manager = setup_modes()
        mode = manager.get_mode(ModeName.HEADLESS)
        assert mode is not None
        assert isinstance(mode, HeadlessMode)

    def test_setup_modes_uses_singleton(self) -> None:
        """Test setup_modes uses singleton if not provided."""
        manager1 = setup_modes()
        manager2 = ModeManager.get_instance()
        assert manager1 is manager2

    def test_setup_modes_with_existing_manager(self) -> None:
        """Test setup_modes with existing manager."""
        existing = ModeManager.get_instance()
        result = setup_modes(existing)
        assert result is existing

    def test_setup_modes_idempotent(self) -> None:
        """Test calling setup_modes twice is safe."""
        manager = setup_modes()
        # Should not raise
        manager = setup_modes(manager)

        # Should still have exactly one of each mode
        assert manager.get_mode(ModeName.PLAN) is not None
        assert manager.get_mode(ModeName.THINKING) is not None
        assert manager.get_mode(ModeName.HEADLESS) is not None

    def test_setup_modes_total_count(self) -> None:
        """Test setup_modes registers correct number of modes."""
        manager = setup_modes()
        modes = manager.list_modes()

        # Should have: Normal (default) + Plan + Thinking + Headless
        assert len(modes) == 4
