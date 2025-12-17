"""Tests for modes package initialization."""

from enum import Enum
from inspect import isclass

import pytest

from code_forge.modes import (
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
        assert isclass(Mode)

    def test_mode_config_exported(self) -> None:
        """Test ModeConfig class is exported."""
        assert isclass(ModeConfig)

    def test_mode_context_exported(self) -> None:
        """Test ModeContext class is exported."""
        assert isclass(ModeContext)

    def test_mode_name_exported(self) -> None:
        """Test ModeName enum is exported."""
        assert isclass(ModeName)
        assert issubclass(ModeName, Enum)
        assert ModeName.NORMAL.value == "normal"

    def test_mode_state_exported(self) -> None:
        """Test ModeState class is exported."""
        assert isclass(ModeState)

    def test_normal_mode_exported(self) -> None:
        """Test NormalMode class is exported."""
        assert isclass(NormalMode)
        assert issubclass(NormalMode, Mode)

    def test_mode_manager_exported(self) -> None:
        """Test ModeManager class is exported."""
        assert isclass(ModeManager)

    def test_plan_mode_exported(self) -> None:
        """Test PlanMode class is exported."""
        assert isclass(PlanMode)
        assert issubclass(PlanMode, Mode)

    def test_thinking_mode_exported(self) -> None:
        """Test ThinkingMode class is exported."""
        assert isclass(ThinkingMode)
        assert issubclass(ThinkingMode, Mode)

    def test_headless_mode_exported(self) -> None:
        """Test HeadlessMode class is exported."""
        assert isclass(HeadlessMode)
        assert issubclass(HeadlessMode, Mode)


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
        assert isinstance(mode, PlanMode)

    def test_setup_modes_registers_thinking(self) -> None:
        """Test setup_modes registers ThinkingMode."""
        manager = setup_modes()
        mode = manager.get_mode(ModeName.THINKING)
        assert isinstance(mode, ThinkingMode)

    def test_setup_modes_registers_headless(self) -> None:
        """Test setup_modes registers HeadlessMode."""
        manager = setup_modes()
        mode = manager.get_mode(ModeName.HEADLESS)
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
        assert isinstance(manager.get_mode(ModeName.PLAN), PlanMode)
        assert isinstance(manager.get_mode(ModeName.THINKING), ThinkingMode)
        assert isinstance(manager.get_mode(ModeName.HEADLESS), HeadlessMode)

    def test_setup_modes_total_count(self) -> None:
        """Test setup_modes registers correct number of modes."""
        manager = setup_modes()
        modes = manager.list_modes()

        # Should have: Normal (default) + Plan + Thinking + Headless
        assert len(modes) == 4
