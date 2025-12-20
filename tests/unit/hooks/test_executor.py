"""Tests for hook executor."""

from __future__ import annotations

import asyncio

import pytest

from code_forge.hooks.events import HookEvent
from code_forge.hooks.executor import (
    HookBlockedError,
    HookExecutor,
    HookResult,
    fire_event,
)
from code_forge.hooks.registry import Hook, HookRegistry


class TestHookResult:
    """Tests for HookResult dataclass."""

    def test_success_property_true(self) -> None:
        """success is True when exit_code=0 and no errors."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=0,
            stdout="ok",
            stderr="",
            duration=0.1,
        )
        assert result.success is True

    def test_success_property_false_nonzero_exit(self) -> None:
        """success is False with non-zero exit code."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=1,
            stdout="",
            stderr="error",
            duration=0.1,
        )
        assert result.success is False

    def test_success_property_false_timeout(self) -> None:
        """success is False when timed out."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=-1,
            stdout="",
            stderr="",
            duration=10.0,
            timed_out=True,
        )
        assert result.success is False

    def test_success_property_false_error(self) -> None:
        """success is False when error is set."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=0,
            stdout="",
            stderr="",
            duration=0.1,
            error="Something went wrong",
        )
        assert result.success is False

    def test_should_continue_true(self) -> None:
        """should_continue is True when exit_code=0."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=0,
            stdout="",
            stderr="",
            duration=0.1,
        )
        assert result.should_continue is True

    def test_should_continue_false(self) -> None:
        """should_continue is False when exit_code!=0."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=1,
            stdout="blocked",
            stderr="",
            duration=0.1,
        )
        assert result.should_continue is False


class TestHookExecutor:
    """Tests for HookExecutor class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        HookRegistry.reset_instance()

    @pytest.fixture
    def registry(self) -> HookRegistry:
        """Get fresh registry."""
        return HookRegistry.get_instance()

    @pytest.fixture
    def executor(self, registry: HookRegistry) -> HookExecutor:
        """Create executor with registry."""
        return HookExecutor(registry=registry)

    @pytest.mark.asyncio
    async def test_execute_no_hooks(self, executor: HookExecutor) -> None:
        """Execute with no hooks returns empty list."""
        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_successful_hook(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Execute successful hook."""
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo hello"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        assert results[0].exit_code == 0
        assert "hello" in results[0].stdout
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_execute_failing_hook(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Execute failing hook."""
        registry.register(Hook(event_pattern="tool:pre_execute", command="exit 1"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        assert results[0].exit_code == 1
        assert results[0].success is False
        assert results[0].should_continue is False

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Hook receives environment variables."""
        registry.register(
            Hook(event_pattern="tool:pre_execute", command="echo $FORGE_TOOL_NAME")
        )

        event = HookEvent.tool_pre_execute("bash", {"command": "ls"})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        assert "bash" in results[0].stdout

    @pytest.mark.asyncio
    async def test_execute_multiple_hooks(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Execute multiple matching hooks."""
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo first"))
        registry.register(Hook(event_pattern="tool:*", command="echo second"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event, stop_on_failure=False)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_stop_on_failure_stops(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """stop_on_failure stops after first failure."""
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo first"))
        registry.register(Hook(event_pattern="tool:pre_execute", command="exit 1"))
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo third"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event, stop_on_failure=True)

        assert len(results) == 2  # First success, then failure
        assert results[0].success is True
        assert results[1].success is False

    @pytest.mark.asyncio
    async def test_stop_on_failure_false_continues(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """stop_on_failure=False continues after failure."""
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo first"))
        registry.register(Hook(event_pattern="tool:pre_execute", command="exit 1"))
        registry.register(Hook(event_pattern="tool:pre_execute", command="echo third"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event, stop_on_failure=False)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_timeout_kills_process(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Hook timeout kills the process."""
        registry.register(
            Hook(event_pattern="tool:pre_execute", command="sleep 10", timeout=0.5)
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        assert results[0].timed_out is True
        assert results[0].success is False
        assert "timed out" in (results[0].error or "").lower()

    @pytest.mark.asyncio
    async def test_max_results_limit(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """max_results limits returned results."""
        for i in range(10):
            registry.register(
                Hook(event_pattern="tool:pre_execute", command=f"echo {i}")
            )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event, max_results=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_hook_working_dir(
        self, executor: HookExecutor, registry: HookRegistry, tmp_path: str
    ) -> None:
        """Hook runs in specified working directory."""
        registry.register(
            Hook(
                event_pattern="tool:pre_execute",
                command="pwd",
                working_dir=str(tmp_path),
            )
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert str(tmp_path) in results[0].stdout

    @pytest.mark.asyncio
    async def test_hook_custom_env(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Hook receives custom environment variables."""
        registry.register(
            Hook(
                event_pattern="tool:pre_execute",
                command="echo $MY_VAR",
                env={"MY_VAR": "custom_value"},
            )
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert "custom_value" in results[0].stdout

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Hook stderr is captured."""
        registry.register(
            Hook(event_pattern="tool:pre_execute", command="echo error >&2")
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert "error" in results[0].stderr

    @pytest.mark.asyncio
    async def test_duration_tracked(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Hook duration is tracked."""
        registry.register(
            Hook(event_pattern="tool:pre_execute", command="sleep 0.1")
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert results[0].duration >= 0.1

    @pytest.mark.asyncio
    async def test_disabled_hooks_not_executed(
        self, executor: HookExecutor, registry: HookRegistry
    ) -> None:
        """Disabled hooks are not executed."""
        registry.register(
            Hook(event_pattern="tool:pre_execute", command="echo enabled", enabled=True)
        )
        registry.register(
            Hook(
                event_pattern="tool:pre_execute", command="echo disabled", enabled=False
            )
        )

        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        assert "enabled" in results[0].stdout


class TestHookBlockedError:
    """Tests for HookBlockedError exception."""

    def test_creation(self) -> None:
        """HookBlockedError stores result."""
        hook = Hook(event_pattern="test", command="exit 1")
        result = HookResult(
            hook=hook,
            exit_code=1,
            stdout="blocked",
            stderr="",
            duration=0.1,
        )
        error = HookBlockedError(result)
        assert error.result is result

    def test_message_format(self) -> None:
        """HookBlockedError message includes details."""
        hook = Hook(event_pattern="tool:pre_execute:bash", command="exit 1")
        result = HookResult(
            hook=hook,
            exit_code=1,
            stdout="",
            stderr="",
            duration=0.1,
        )
        error = HookBlockedError(result)
        assert "tool:pre_execute:bash" in str(error)
        assert "exit code 1" in str(error)

    def test_is_exception(self) -> None:
        """HookBlockedError is an Exception."""
        hook = Hook(event_pattern="test", command="test")
        result = HookResult(
            hook=hook,
            exit_code=1,
            stdout="",
            stderr="",
            duration=0.1,
        )
        error = HookBlockedError(result)
        assert isinstance(error, Exception)


class TestFireEvent:
    """Tests for fire_event convenience function."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        HookRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_fire_event_basic(self) -> None:
        """fire_event executes hooks."""
        registry = HookRegistry.get_instance()
        registry.register(Hook(event_pattern="tool:*", command="echo fired"))

        event = HookEvent.tool_pre_execute("bash", {})
        results = await fire_event(event)

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_fire_event_with_custom_executor(self) -> None:
        """fire_event uses custom executor."""
        registry = HookRegistry()  # Not the singleton
        registry.register(Hook(event_pattern="tool:*", command="echo custom"))

        executor = HookExecutor(registry=registry)
        event = HookEvent.tool_pre_execute("bash", {})
        results = await fire_event(event, executor=executor)

        assert len(results) == 1
        assert "custom" in results[0].stdout

    @pytest.mark.asyncio
    async def test_fire_event_stop_on_failure(self) -> None:
        """fire_event passes stop_on_failure."""
        registry = HookRegistry.get_instance()
        registry.register(Hook(event_pattern="tool:*", command="exit 1"))
        registry.register(Hook(event_pattern="tool:*", command="echo second"))

        event = HookEvent.tool_pre_execute("bash", {})

        # With stop_on_failure=True (default)
        results = await fire_event(event, stop_on_failure=True)
        assert len(results) == 1

        # With stop_on_failure=False
        results = await fire_event(event, stop_on_failure=False)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fire_event_no_hooks(self) -> None:
        """fire_event with no hooks returns empty list."""
        event = HookEvent.tool_pre_execute("bash", {})
        results = await fire_event(event)
        assert results == []


class TestHookExecutorEdgeCases:
    """Tests for edge cases in hook execution."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset singleton before each test."""
        HookRegistry.reset_instance()

    @pytest.mark.asyncio
    async def test_invalid_command(self) -> None:
        """Invalid command is handled gracefully."""
        registry = HookRegistry.get_instance()
        registry.register(
            Hook(
                event_pattern="tool:*", command="/nonexistent/command/12345abc"
            )
        )

        executor = HookExecutor(registry=registry)
        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1
        # Should either have error or non-zero exit code
        assert results[0].exit_code != 0 or isinstance(results[0].error, str)

    @pytest.mark.asyncio
    async def test_empty_command(self) -> None:
        """Empty command is handled."""
        registry = HookRegistry.get_instance()
        registry.register(Hook(event_pattern="tool:*", command=""))

        executor = HookExecutor(registry=registry)
        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_multiline_command(self) -> None:
        """Multiline commands work."""
        registry = HookRegistry.get_instance()
        registry.register(
            Hook(
                event_pattern="tool:*",
                command="echo line1\necho line2",
            )
        )

        executor = HookExecutor(registry=registry)
        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert "line1" in results[0].stdout
        assert "line2" in results[0].stdout

    @pytest.mark.asyncio
    async def test_unicode_in_output(self) -> None:
        """Unicode in output is handled."""
        registry = HookRegistry.get_instance()
        registry.register(Hook(event_pattern="tool:*", command="echo 'Hello 世界'"))

        executor = HookExecutor(registry=registry)
        event = HookEvent.tool_pre_execute("bash", {})
        results = await executor.execute_hooks(event)

        assert "世界" in results[0].stdout

    @pytest.mark.asyncio
    async def test_special_chars_in_env(self) -> None:
        """Special characters in env vars are handled."""
        event = HookEvent.tool_pre_execute(
            "bash",
            {"command": 'echo "hello $world"'},
        )
        env = event.to_env()
        assert "FORGE_TOOL_ARGS" in env

        registry = HookRegistry.get_instance()
        registry.register(Hook(event_pattern="tool:*", command="echo ok"))

        executor = HookExecutor(registry=registry)
        results = await executor.execute_hooks(event)

        assert results[0].success is True
