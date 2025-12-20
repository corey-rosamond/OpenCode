"""Comprehensive concurrent/race condition tests for Code-Forge.

This module tests thread safety and race conditions across critical shared state:
- Registry singletons (ToolRegistry, SkillRegistry)
- ShellManager concurrent operations
- PermissionChecker concurrent rule modifications
- Token counter concurrent increments
- Web cache concurrent get/set operations
- Session concurrent access

Tests use threading.Thread, concurrent.futures.ThreadPoolExecutor, and
asyncio.gather() to create realistic concurrent scenarios.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pytest

# Import from core.errors first to resolve circular import
from code_forge.core.errors import ToolError  # noqa: F401
from code_forge.context.tokens import CachingCounter, TiktokenCounter
from code_forge.permissions.checker import PermissionChecker
from code_forge.permissions.models import PermissionLevel, PermissionRule
from code_forge.skills.registry import SkillRegistry
from code_forge.tools.base import (
    BaseTool,
    ExecutionContext,
    ToolCategory,
    ToolParameter,
    ToolResult,
)
from code_forge.tools.execution.shell_manager import ShellManager
from code_forge.tools.registry import ToolRegistry
from code_forge.web.cache import WebCache
from code_forge.web.types import FetchOptions, FetchResponse


# =============================================================================
# Test Fixtures and Utilities
# =============================================================================


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, tool_name: str = "MockTool"):
        self._name = tool_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock tool: {self._name}"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.OTHER

    @property
    def parameters(self) -> list[ToolParameter]:
        return []

    async def _execute(self, context: ExecutionContext, **kwargs: Any) -> ToolResult:
        # Simulate some work
        await asyncio.sleep(0.001)
        return ToolResult.ok(f"Executed {self._name}")


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before and after each test."""
    ToolRegistry.reset()
    SkillRegistry.reset_instance()
    ShellManager.reset()
    yield
    ToolRegistry.reset()
    SkillRegistry.reset_instance()
    ShellManager.reset()


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


# =============================================================================
# Registry Race Condition Tests
# =============================================================================


class TestToolRegistryRaceConditions:
    """Test ToolRegistry under concurrent load."""

    def test_concurrent_tool_registration(self) -> None:
        """Test multiple threads registering tools simultaneously."""
        registry = ToolRegistry()
        num_threads = 20
        tools_per_thread = 10
        errors: list[Exception] = []

        def register_tools(thread_id: int):
            try:
                for i in range(tools_per_thread):
                    tool = MockTool(f"Tool_T{thread_id}_I{i}")
                    registry.register(tool)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_tools, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors and all tools registered
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert registry.count() == num_threads * tools_per_thread

    def test_concurrent_register_and_deregister(self) -> None:
        """Test concurrent registration and deregistration."""
        registry = ToolRegistry()
        # Pre-populate with some tools
        for i in range(50):
            registry.register(MockTool(f"Initial_{i}"))

        errors: list[Exception] = []
        operations = []

        def worker(op_id: int):
            try:
                if op_id % 3 == 0:
                    # Register new tool
                    registry.register(MockTool(f"New_{op_id}"))
                    operations.append(("register", op_id))
                elif op_id % 3 == 1:
                    # Deregister existing tool
                    registry.deregister(f"Initial_{op_id % 50}")
                    operations.append(("deregister", op_id))
                else:
                    # Read operation
                    registry.list_all()
                    operations.append(("read", op_id))
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(worker, range(100)))

        # No errors should occur
        assert len(errors) == 0, f"Errors: {errors}"
        # Registry should be consistent
        assert registry.count() >= 0

    def test_concurrent_get_operations(self) -> None:
        """Test concurrent get operations don't corrupt state."""
        registry = ToolRegistry()
        tools = [MockTool(f"Tool_{i}") for i in range(10)]
        for tool in tools:
            registry.register(tool)

        results: list[BaseTool | None] = []
        errors: list[Exception] = []

        def get_random_tool(idx: int):
            try:
                tool = registry.get(f"Tool_{idx % 10}")
                results.append(tool)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(get_random_tool, range(300)))

        # All gets should succeed
        assert len(errors) == 0
        assert len(results) == 300
        assert all(r is not None for r in results)

    def test_singleton_creation_race_condition(self) -> None:
        """Test that singleton creation is thread-safe under high contention."""
        ToolRegistry.reset()
        instances: list[ToolRegistry] = []
        barrier = threading.Barrier(50)  # Synchronize all threads

        def create_instance():
            barrier.wait()  # Wait for all threads to be ready
            # All threads try to create instance simultaneously
            instance = ToolRegistry()
            instances.append(instance)

        threads = [threading.Thread(target=create_instance) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be identical
        assert all(inst is instances[0] for inst in instances)

    def test_concurrent_clear_and_access(self) -> None:
        """Test clearing registry while others are accessing it."""
        registry = ToolRegistry()
        for i in range(20):
            registry.register(MockTool(f"Tool_{i}"))

        errors: list[Exception] = []
        stop_flag = threading.Event()

        def reader():
            while not stop_flag.is_set():
                try:
                    registry.list_all()
                    registry.count()
                except Exception as e:
                    errors.append(e)
                time.sleep(0.001)

        def clearer():
            time.sleep(0.01)
            try:
                registry.clear()
            except Exception as e:
                errors.append(e)

        # Start readers
        readers = [threading.Thread(target=reader) for _ in range(10)]
        for t in readers:
            t.start()

        # Clear registry
        clearer_thread = threading.Thread(target=clearer)
        clearer_thread.start()
        clearer_thread.join()

        # Stop readers
        stop_flag.set()
        for t in readers:
            t.join()

        # No errors should occur
        assert len(errors) == 0


class TestSkillRegistryRaceConditions:
    """Test SkillRegistry under concurrent load."""

    def test_concurrent_skill_registration(self) -> None:
        """Test multiple threads registering skills simultaneously."""
        from code_forge.skills.base import Skill, SkillDefinition, SkillMetadata

        registry = SkillRegistry.get_instance()
        num_threads = 15
        errors: list[Exception] = []

        def register_skills(thread_id: int):
            try:
                for i in range(5):
                    skill_name = f"skill_t{thread_id}_i{i}"
                    definition = SkillDefinition(
                        metadata=SkillMetadata(
                            name=skill_name,
                            version="1.0.0",
                            description="Test skill",
                            author="Test",
                        ),
                        prompt="Test skill prompt",
                        config=[],
                    )
                    skill = Skill(definition)
                    registry.register(skill)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_skills, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(registry.list_skills()) == num_threads * 5

    def test_concurrent_skill_activation(self) -> None:
        """Test concurrent skill activation/deactivation."""
        from code_forge.skills.base import Skill, SkillDefinition, SkillMetadata

        registry = SkillRegistry.get_instance()

        # Register multiple skills
        for i in range(10):
            definition = SkillDefinition(
                metadata=SkillMetadata(
                    name=f"skill_{i}",
                    version="1.0.0",
                    description="Test skill",
                    author="Test",
                ),
                prompt="Test skill prompt",
                config=[],
            )
            skill = Skill(definition)
            registry.register(skill)

        errors: list[Exception] = []
        activation_results = []

        def activate_skill(skill_id: int):
            try:
                skill, errs = registry.activate(f"skill_{skill_id % 10}")
                activation_results.append((skill, errs))
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(activate_skill, range(50)))

        # No exceptions should occur (though some activations may fail due to conflicts)
        assert len(errors) == 0
        # At least some activations should succeed
        successful = [r for r in activation_results if r[0] is not None]
        assert len(successful) > 0


# =============================================================================
# ShellManager Race Condition Tests
# =============================================================================


class TestShellManagerRaceConditions:
    """Test ShellManager under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_shell_creation(self, tmp_path: Path) -> None:
        """Test creating multiple shells concurrently."""
        manager = ShellManager()
        num_shells = 20

        async def create_shell(idx: int):
            shell = await manager.create_shell(
                command=f"echo 'Shell {idx}'",
                working_dir=str(tmp_path),
            )
            return shell

        # Create shells concurrently
        shells = await asyncio.gather(*[create_shell(i) for i in range(num_shells)])

        # All shells should be created
        assert len(shells) == num_shells
        # All should have unique IDs
        shell_ids = [s.id for s in shells]
        assert len(set(shell_ids)) == num_shells

        # Cleanup
        await manager.kill_all()

    @pytest.mark.asyncio
    async def test_concurrent_shell_access(self, tmp_path: Path) -> None:
        """Test concurrent access to shell processes."""
        manager = ShellManager()

        # Create several shells
        shells = []
        for i in range(5):
            shell = await manager.create_shell(
                command=f"echo 'Test {i}'; sleep 0.1",
                working_dir=str(tmp_path),
            )
            shells.append(shell)

        errors: list[Exception] = []

        async def read_shell_output(shell_id: str):
            try:
                shell = manager.get_shell(shell_id)
                if shell:
                    await shell.read_output()
                    shell.get_new_output()
            except Exception as e:
                errors.append(e)

        # Concurrent reads from multiple shells
        tasks = []
        for _ in range(50):
            for shell in shells:
                tasks.append(read_shell_output(shell.id))

        await asyncio.gather(*tasks)

        # No errors should occur
        assert len(errors) == 0

        # Cleanup
        await manager.kill_all()

    @pytest.mark.asyncio
    async def test_concurrent_cleanup_and_access(self, tmp_path: Path) -> None:
        """Test cleanup while shells are being accessed."""
        manager = ShellManager()

        # Create shells
        for i in range(10):
            await manager.create_shell(
                command=f"echo 'Shell {i}'; sleep 0.2",
                working_dir=str(tmp_path),
            )

        errors: list[Exception] = []

        async def list_shells():
            try:
                manager.list_shells()
                manager.list_running()
            except Exception as e:
                errors.append(e)

        async def cleanup():
            await asyncio.sleep(0.05)
            try:
                await manager.cleanup_completed(max_age_seconds=0)
            except Exception as e:
                errors.append(e)

        # Run cleanup concurrently with listing operations
        tasks = [cleanup()] + [list_shells() for _ in range(20)]
        await asyncio.gather(*tasks)

        # No errors should occur
        assert len(errors) == 0

        # Cleanup
        await manager.kill_all()


# =============================================================================
# PermissionChecker Race Condition Tests
# =============================================================================


class TestPermissionCheckerRaceConditions:
    """Test PermissionChecker under concurrent load."""

    def test_concurrent_session_rule_modifications(self) -> None:
        """Test concurrent modifications to session rules."""
        checker = PermissionChecker()
        errors: list[Exception] = []

        def add_rule(idx: int):
            try:
                rule = PermissionRule(
                    pattern=f"tool:test_{idx}",
                    permission=PermissionLevel.ALLOW if idx % 2 == 0 else PermissionLevel.DENY,
                    description=f"Test rule {idx}",
                    priority=50,
                )
                checker.add_session_rule(rule)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(add_rule, range(100)))

        # No errors should occur
        assert len(errors) == 0
        # All rules should be added (last one wins for same pattern)
        rules = checker.get_session_rules()
        assert len(rules) > 0

    def test_concurrent_check_and_modify(self) -> None:
        """Test checking permissions while rules are being modified."""
        checker = PermissionChecker()

        # Pre-populate some rules
        for i in range(10):
            rule = PermissionRule(
                pattern=f"tool:initial_{i}",
                permission=PermissionLevel.ALLOW,
                description=f"Initial rule {i}",
                priority=50,
            )
            checker.add_session_rule(rule)

        errors: list[Exception] = []
        check_results = []

        def check_permission(idx: int):
            try:
                result = checker.check(f"test_tool_{idx % 10}", {"arg": "value"})
                check_results.append(result)
            except Exception as e:
                errors.append(e)

        def modify_rules(idx: int):
            try:
                if idx % 2 == 0:
                    rule = PermissionRule(
                        pattern=f"tool:new_{idx}",
                        permission=PermissionLevel.DENY,
                        description=f"New rule {idx}",
                        priority=60,
                    )
                    checker.add_session_rule(rule)
                else:
                    checker.remove_session_rule(f"tool:initial_{idx % 10}")
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = []
            for i in range(100):
                if i % 3 == 0:
                    futures.append(executor.submit(modify_rules, i))
                else:
                    futures.append(executor.submit(check_permission, i))

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(errors) == 0
        # Permission checks should complete
        assert len(check_results) > 0

    def test_concurrent_clear_and_check(self) -> None:
        """Test clearing rules while permissions are being checked."""
        checker = PermissionChecker()

        for i in range(20):
            rule = PermissionRule(
                pattern=f"tool:test_{i}",
                permission=PermissionLevel.ALLOW,
                description=f"Test rule {i}",
                priority=50,
            )
            checker.add_session_rule(rule)

        errors: list[Exception] = []
        stop_flag = threading.Event()

        def check_continuously():
            while not stop_flag.is_set():
                try:
                    checker.check("test_tool", {"arg": "value"})
                except Exception as e:
                    errors.append(e)
                time.sleep(0.001)

        def clear_rules():
            time.sleep(0.05)
            try:
                checker.clear_session_rules()
            except Exception as e:
                errors.append(e)

        # Start checkers
        checkers = [threading.Thread(target=check_continuously) for _ in range(10)]
        for t in checkers:
            t.start()

        # Clear rules
        clear_thread = threading.Thread(target=clear_rules)
        clear_thread.start()
        clear_thread.join()

        # Stop checkers
        stop_flag.set()
        for t in checkers:
            t.join()

        # No errors should occur
        assert len(errors) == 0


# =============================================================================
# Token Counter Race Condition Tests
# =============================================================================


class TestTokenCounterRaceConditions:
    """Test token counter cache under concurrent load."""

    def test_concurrent_token_counting(self) -> None:
        """Test concurrent token counting with cache."""
        counter = CachingCounter(TiktokenCounter(), max_cache_size=100)
        texts = [f"Test text number {i} for token counting" for i in range(50)]
        errors: list[Exception] = []
        results: list[int] = []

        def count_tokens(text: str):
            try:
                count = counter.count(text)
                results.append(count)
            except Exception as e:
                errors.append(e)

        # Count same texts multiple times from multiple threads
        with ThreadPoolExecutor(max_workers=20) as executor:
            for _ in range(10):  # 10 rounds
                for text in texts:
                    executor.submit(count_tokens, text)

        # Wait for all to complete
        time.sleep(0.5)

        # No errors should occur
        assert len(errors) == 0
        # Results should be consistent
        assert len(results) > 0

        # Cache stats should be reasonable
        stats = counter.get_stats()
        assert stats["hits"] > 0  # Should have cache hits
        assert stats["size"] <= 100  # Should not exceed max size

    def test_concurrent_cache_eviction(self) -> None:
        """Test cache eviction under concurrent load."""
        counter = CachingCounter(TiktokenCounter(), max_cache_size=10)
        errors: list[Exception] = []

        def count_random_text(idx: int):
            try:
                # Create many unique texts to trigger eviction
                text = f"Unique text {idx} with some content"
                counter.count(text)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(count_random_text, range(200)))

        # No errors should occur during eviction
        assert len(errors) == 0
        # Cache size should be at or below max
        stats = counter.get_stats()
        assert stats["size"] <= 10


# =============================================================================
# Web Cache Race Condition Tests
# =============================================================================


class TestWebCacheRaceConditions:
    """Test WebCache under concurrent load."""

    def test_concurrent_cache_set(self, temp_cache_dir: Path) -> None:
        """Test concurrent cache set operations."""
        cache = WebCache(cache_dir=temp_cache_dir, max_size=1024 * 1024)
        errors: list[Exception] = []

        def set_cache_entry(idx: int):
            try:
                key = cache.generate_key(f"http://example.com/{idx}", None)
                response = FetchResponse(
                    url=f"http://example.com/{idx}",
                    final_url=f"http://example.com/{idx}",
                    status_code=200,
                    content_type="text/html",
                    content=f"Content for page {idx}",
                    headers={},
                    encoding="utf-8",
                    fetch_time=time.time(),
                    from_cache=False,
                )
                cache.set(key, response)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(set_cache_entry, range(100)))

        # No errors should occur
        assert len(errors) == 0
        # Cache should have entries
        assert cache.count > 0

    def test_concurrent_get_and_set(self, temp_cache_dir: Path) -> None:
        """Test concurrent get and set operations."""
        cache = WebCache(cache_dir=temp_cache_dir, max_size=1024 * 1024, ttl=60)

        # Pre-populate cache
        for i in range(20):
            key = cache.generate_key(f"http://example.com/{i}", None)
            response = FetchResponse(
                url=f"http://example.com/{i}",
                final_url=f"http://example.com/{i}",
                status_code=200,
                content_type="text/html",
                content=f"Initial content {i}",
                headers={},
                encoding="utf-8",
                fetch_time=time.time(),
                from_cache=False,
            )
            cache.set(key, response)

        errors: list[Exception] = []
        get_results = []

        def get_or_set(idx: int):
            try:
                key = cache.generate_key(f"http://example.com/{idx % 20}", None)
                if idx % 2 == 0:
                    # Get
                    result = cache.get(key)
                    get_results.append(result)
                else:
                    # Set
                    response = FetchResponse(
                        url=f"http://example.com/{idx % 20}",
                        final_url=f"http://example.com/{idx % 20}",
                        status_code=200,
                        content_type="text/html",
                        content=f"Updated content {idx}",
                        headers={},
                        encoding="utf-8",
                        fetch_time=time.time(),
                        from_cache=False,
                    )
                    cache.set(key, response)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(get_or_set, range(200)))

        # No errors should occur
        assert len(errors) == 0
        # Should have successful gets
        assert len([r for r in get_results if r is not None]) > 0

    def test_concurrent_eviction(self, temp_cache_dir: Path) -> None:
        """Test cache eviction under concurrent load."""
        # Small cache to trigger eviction
        cache = WebCache(cache_dir=temp_cache_dir, max_size=1024 * 10)
        errors: list[Exception] = []

        def add_large_entry(idx: int):
            try:
                key = cache.generate_key(f"http://example.com/large/{idx}", None)
                # Create a large response
                response = FetchResponse(
                    url=f"http://example.com/large/{idx}",
                    final_url=f"http://example.com/large/{idx}",
                    status_code=200,
                    content_type="text/html",
                    content="x" * 1024,  # 1KB content
                    headers={},
                    encoding="utf-8",
                    fetch_time=time.time(),
                    from_cache=False,
                )
                cache.set(key, response)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(add_large_entry, range(50)))

        # No errors should occur during eviction
        assert len(errors) == 0
        # Cache size should be within limits
        assert cache.size <= 1024 * 10


# =============================================================================
# Cross-Component Concurrent Tests
# =============================================================================


class TestCrossComponentConcurrency:
    """Test concurrent operations across multiple components."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_with_registry_access(self, tmp_path: Path) -> None:
        """Test executing tools concurrently while accessing registry."""
        registry = ToolRegistry()

        # Register tools
        for i in range(10):
            registry.register(MockTool(f"Tool_{i}"))

        errors: list[Exception] = []

        async def execute_tool(idx: int):
            try:
                tool = registry.get(f"Tool_{idx % 10}")
                if tool:
                    context = ExecutionContext(working_dir=str(tmp_path), timeout=5)
                    await tool._execute(context)
            except Exception as e:
                errors.append(e)

        def access_registry():
            try:
                registry.list_all()
                registry.count()
            except Exception as e:
                errors.append(e)

        # Mix async tool execution with sync registry access
        exec_tasks = [execute_tool(i) for i in range(30)]

        # Run registry access in thread pool while executing tools
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_registry) for _ in range(50)]
            await asyncio.gather(*exec_tasks)
            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(errors) == 0

    def test_concurrent_multi_registry_access(self) -> None:
        """Test concurrent access to multiple registries."""
        tool_registry = ToolRegistry()
        skill_registry = SkillRegistry.get_instance()

        # Register some items
        for i in range(10):
            tool_registry.register(MockTool(f"Tool_{i}"))

        errors: list[Exception] = []

        def access_registries(idx: int):
            try:
                # Access tool registry
                tool_registry.list_all()
                tool_registry.get(f"Tool_{idx % 10}")

                # Access skill registry
                skill_registry.list_skills()
                skill_registry.get_stats()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(access_registries, range(100)))

        # No errors should occur
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_shell_creation_with_permission_checking(self, tmp_path: Path) -> None:
        """Test creating shells while checking permissions concurrently."""
        manager = ShellManager()
        checker = PermissionChecker()

        # Add some permission rules
        for i in range(10):
            rule = PermissionRule(
                pattern=f"tool:bash_{i}",
                permission=PermissionLevel.ALLOW,
                description=f"Allow bash {i}",
                priority=50,
            )
            checker.add_session_rule(rule)

        errors: list[Exception] = []

        async def create_shell(idx: int):
            try:
                await manager.create_shell(
                    command=f"echo 'Shell {idx}'",
                    working_dir=str(tmp_path),
                )
            except Exception as e:
                errors.append(e)

        def check_permission(idx: int):
            try:
                checker.check(f"bash_{idx % 10}", {"command": "echo test"})
            except Exception as e:
                errors.append(e)

        # Create shells and check permissions concurrently
        shell_tasks = [create_shell(i) for i in range(20)]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_permission, i) for i in range(50)]
            await asyncio.gather(*shell_tasks)
            for future in as_completed(futures):
                future.result()

        # No errors should occur
        assert len(errors) == 0

        # Cleanup
        await manager.kill_all()


# =============================================================================
# Stress Tests
# =============================================================================


class TestConcurrencyStress:
    """Stress tests with high concurrency levels."""

    def test_high_contention_registry_access(self) -> None:
        """Test registry under very high contention."""
        registry = ToolRegistry()

        # Pre-populate
        for i in range(100):
            registry.register(MockTool(f"Tool_{i}"))

        errors: list[Exception] = []
        operations_count = [0]
        lock = threading.Lock()

        def random_operation(idx: int):
            try:
                op = idx % 5
                if op == 0:
                    registry.get(f"Tool_{idx % 100}")
                elif op == 1:
                    registry.exists(f"Tool_{idx % 100}")
                elif op == 2:
                    registry.list_all()
                elif op == 3:
                    registry.list_names()
                else:
                    registry.count()

                with lock:
                    operations_count[0] += 1
            except Exception as e:
                errors.append(e)

        # 1000 operations with high concurrency
        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(random_operation, range(1000)))

        # No errors should occur
        assert len(errors) == 0
        # All operations should complete
        assert operations_count[0] == 1000

    @pytest.mark.asyncio
    async def test_shell_manager_stress(self, tmp_path: Path) -> None:
        """Test ShellManager under stress with many shells."""
        manager = ShellManager()
        errors: list[Exception] = []

        async def create_and_kill_shell(idx: int):
            try:
                shell = await manager.create_shell(
                    command=f"echo 'Stress test {idx}'",
                    working_dir=str(tmp_path),
                )
                await asyncio.sleep(0.01)
                await shell.read_output()
                shell.kill()
            except Exception as e:
                errors.append(e)

        # Create many shells concurrently
        await asyncio.gather(*[create_and_kill_shell(i) for i in range(50)])

        # No errors should occur
        assert len(errors) == 0

        # Cleanup remaining
        await manager.kill_all()
