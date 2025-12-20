# Concurrency and Race Condition Tests

## Overview

This document describes the comprehensive concurrent/race condition tests added to the Code-Forge test suite. These tests address **TEST-003** by providing extensive coverage of thread safety and race conditions across critical shared state components.

**Test File**: `tests/integration/test_concurrency.py`
**Total Tests**: 23
**Status**: All tests passing ✓

## Test Categories

### 1. Registry Race Conditions (5 tests)

Tests for `ToolRegistry` singleton under concurrent load:

- **test_concurrent_tool_registration**: 20 threads each registering 10 tools simultaneously (200 total tools)
- **test_concurrent_register_and_deregister**: Mixed operations with 100 concurrent workers doing registration, deregistration, and reads
- **test_concurrent_get_operations**: 30 threads performing 300 concurrent get operations
- **test_singleton_creation_race_condition**: 50 threads simultaneously attempting to create the singleton instance using a barrier for maximum contention
- **test_concurrent_clear_and_access**: 10 reader threads continuously accessing registry while one thread clears it

**Purpose**: Verifies that the `ToolRegistry` singleton and its RLock-protected operations remain consistent under high concurrent load, with no data corruption or missing updates.

### 2. Skill Registry Race Conditions (2 tests)

Tests for `SkillRegistry` concurrent operations:

- **test_concurrent_skill_registration**: 15 threads each registering 5 skills concurrently
- **test_concurrent_skill_activation**: 20 workers attempting to activate skills concurrently (tests single active skill invariant)

**Purpose**: Ensures skill registration and activation/deactivation are thread-safe, and that only one skill can be active at a time.

### 3. Shell Manager Race Conditions (3 tests)

Tests for `ShellManager` async concurrent operations:

- **test_concurrent_shell_creation**: Creates 20 shells concurrently using `asyncio.gather()`
- **test_concurrent_shell_access**: 50 concurrent reads from 5 different shell processes
- **test_concurrent_cleanup_and_access**: Cleanup operations running concurrently with shell listing

**Purpose**: Verifies that shell creation, output reading, and cleanup operations work correctly when multiple async tasks access the shell manager simultaneously.

### 4. Permission Checker Race Conditions (3 tests)

Tests for `PermissionChecker` concurrent rule modifications:

- **test_concurrent_session_rule_modifications**: 20 threads adding 100 session rules concurrently
- **test_concurrent_check_and_modify**: 30 workers mixing permission checks with rule modifications
- **test_concurrent_clear_and_check**: 10 threads continuously checking permissions while rules are cleared

**Purpose**: Ensures permission checking and rule modifications are thread-safe, with consistent results even when rules are being modified concurrently.

### 5. Token Counter Race Conditions (2 tests)

Tests for `CachingCounter` thread safety:

- **test_concurrent_token_counting**: 20 threads counting tokens from 50 texts over 10 rounds (verifies cache hits)
- **test_concurrent_cache_eviction**: 30 threads creating 200 unique texts to trigger LRU eviction

**Purpose**: Verifies that the token counter's LRU cache remains consistent during concurrent access and eviction.

### 6. Web Cache Race Conditions (3 tests)

Tests for `WebCache` concurrent operations:

- **test_concurrent_cache_set**: 20 threads setting 100 cache entries concurrently
- **test_concurrent_get_and_set**: 30 workers mixing get and set operations on 20 shared cache keys
- **test_concurrent_eviction**: 20 threads adding large entries to trigger cache eviction

**Purpose**: Ensures web cache operations (get, set, eviction) are thread-safe and size tracking remains accurate.

### 7. Cross-Component Concurrency (3 tests)

Tests for concurrent operations across multiple components:

- **test_concurrent_tool_execution_with_registry_access**: 30 async tool executions while 50 threads access the registry
- **test_concurrent_multi_registry_access**: 30 threads accessing both tool and skill registries simultaneously
- **test_shell_creation_with_permission_checking**: 20 shells being created while 50 threads check permissions

**Purpose**: Verifies that different components can operate concurrently without interfering with each other.

### 8. Stress Tests (2 tests)

High-concurrency stress tests:

- **test_high_contention_registry_access**: 50 workers performing 1000 random registry operations (get, exists, list_all, etc.)
- **test_shell_manager_stress**: Creates and destroys 50 shells concurrently

**Purpose**: Validates system behavior under very high concurrent load to expose potential race conditions that only manifest under stress.

## Key Testing Techniques

### Thread Synchronization
- Uses `threading.Barrier` to synchronize threads for maximum contention
- `ThreadPoolExecutor` for controlled concurrent execution
- Stop flags and sleeps for continuous background operations

### Async Concurrency
- `asyncio.gather()` for parallel async operations
- Mixed sync (threading) and async (asyncio) operations
- Proper cleanup to avoid event loop warnings

### Error Detection
- All tests collect exceptions from all threads
- Assertions verify no errors occurred
- Data consistency checks (counts, state invariants)

## Running the Tests

```bash
# Run all concurrency tests
pytest tests/integration/test_concurrency.py -v

# Run a specific test category
pytest tests/integration/test_concurrency.py::TestToolRegistryRaceConditions -v

# Run with increased timeout for slower systems
pytest tests/integration/test_concurrency.py -v --timeout=300
```

## Coverage Summary

The tests cover all critical shared state areas mentioned in TEST-003:

✅ **Registry/Singleton Race Conditions**
- ToolRegistry concurrent registration, deregistration, access
- SkillRegistry concurrent registration and activation
- ShellManager concurrent shell creation and access
- Singleton creation under high contention

✅ **Shared State Access**
- Token counter concurrent increments and cache eviction
- Web cache concurrent get/set operations
- Permission checker concurrent rule modifications

✅ **Concurrent Tool Execution**
- Multiple async tools running in parallel
- Tool execution with concurrent registry access

✅ **Cross-Component Operations**
- Shell creation with permission checking
- Multi-registry concurrent access
- Mixed sync/async operations

## Test Execution Time

Average execution time: ~2-5 seconds for all 23 tests

- Fast tests: Registry operations, token counting, cache operations (~0.1-0.5s each)
- Medium tests: Permission checking, skill operations (~0.5-1s each)
- Slower tests: Shell creation, async operations (~1-2s each)

## Future Enhancements

Potential areas for additional concurrent testing:

1. Session manager concurrent session creation/access
2. Config loader concurrent reloads
3. File system operations (concurrent reads/writes to same file)
4. Session storage concurrent save/load
5. Hook system concurrent hook execution
6. Plugin system concurrent plugin loading

## Notes

- All tests use fixtures that properly reset singletons to avoid test pollution
- Tests use realistic concurrency levels (10-50 threads) based on typical usage patterns
- Async tests properly handle event loop cleanup
- Tests are designed to be deterministic despite concurrent execution
