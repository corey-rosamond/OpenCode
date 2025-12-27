# Code-Forge Test Suite

This directory contains the comprehensive test suite for Code-Forge, providing 4,800+ tests covering all major subsystems.

## Test Structure

```
tests/
├── agents/          # Agent system tests (712 tests)
│   ├── test_all_agents.py    # Parametrized tests for all 20 agent types
│   ├── test_base.py          # Base agent functionality
│   ├── test_builtin.py       # Built-in agent implementations
│   ├── test_executor.py      # Agent execution engine
│   ├── test_manager.py       # Agent lifecycle management
│   ├── test_result.py        # Agent result handling
│   └── test_types.py         # Agent type definitions and registry
│
├── async/           # Async utilities tests
│   ├── test_executor.py      # Async executor tests
│   ├── test_task_manager.py  # Task lifecycle tests
│   └── test_scheduler.py     # Work scheduling tests
│
├── commands/        # CLI command tests
│   ├── test_base.py          # Command base classes
│   ├── test_registry.py      # Command registration
│   └── test_*.py             # Individual command tests
│
├── e2e/             # End-to-end tests
│   └── test_sessions_e2e.py  # Full session lifecycle tests
│
├── git/             # Git integration tests
│   ├── test_operations.py    # Git operation wrappers
│   └── test_diff.py          # Diff parsing and handling
│
├── github/          # GitHub API tests
│   ├── test_client.py        # GitHub client tests
│   └── test_operations.py    # PR/issue operations
│
├── integration/     # Integration tests
│   ├── test_concurrency.py   # Race condition tests
│   └── test_*.py             # Cross-module integration
│
├── mcp/             # Model Context Protocol tests
│   ├── test_client.py        # MCP client tests
│   ├── test_config.py        # MCP configuration
│   ├── test_manager.py       # MCP lifecycle management
│   └── test_tools.py         # MCP tool integration
│
├── plugins/         # Plugin system tests
│   ├── test_manager.py       # Plugin loading/unloading
│   └── test_hooks.py         # Hook system tests
│
├── skills/          # Skill system tests
│   ├── test_base.py          # Skill base classes
│   ├── test_registry.py      # Skill registration
│   └── test_parser.py        # Skill definition parsing
│
├── unit/            # Unit tests by module
│   ├── cli/                  # CLI module tests
│   │   ├── test_setup.py     # Setup wizard tests
│   │   ├── test_dependencies.py  # DI container tests
│   │   └── test_main.py      # Entry point tests
│   ├── config/               # Configuration tests
│   │   └── test_loader.py    # Config loading/merging
│   ├── context/              # Context management tests
│   │   └── test_strategies.py  # Context window strategies
│   ├── langchain/            # LangChain integration tests
│   │   └── test_llm.py       # LLM wrapper tests
│   ├── llm/                  # LLM module tests
│   │   └── test_models.py    # Message/request models
│   ├── modes/                # Mode system tests
│   │   ├── test_manager.py   # Mode switching
│   │   └── test_headless.py  # Headless mode
│   ├── permissions/          # Permission tests
│   │   ├── test_config.py    # Permission configuration
│   │   └── test_prompt.py    # Permission prompting
│   └── tools/                # Tool system tests
│       ├── test_executor.py  # Tool execution
│       ├── test_registry.py  # Tool registration
│       └── file/             # File tool tests
│           ├── test_read.py
│           ├── test_write.py
│           ├── test_glob.py
│           └── test_utils.py
│
├── web/             # Web integration tests
│   ├── test_search.py        # Web search tests
│   └── test_fetch.py         # URL fetching tests
│
├── conftest.py      # Shared fixtures
└── README.md        # This file
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Categories
```bash
# Unit tests only
pytest tests/unit/

# Agent tests only
pytest tests/agents/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

### Run with Coverage
```bash
pytest --cov=src/code_forge --cov-report=html
```

### Run in Parallel
```bash
pytest -n auto
```

### Run Specific Test File
```bash
pytest tests/unit/cli/test_setup.py -v
```

### Run Specific Test Class or Method
```bash
pytest tests/agents/test_all_agents.py::TestAllAgentsCreation -v
pytest tests/agents/test_all_agents.py::TestAllAgentsCreation::test_agent_instantiation -v
```

### Run with Verbose Output
```bash
pytest -v --tb=short
```

## Test Categories

### Unit Tests (`tests/unit/`)
Tests for individual modules in isolation. Mock external dependencies.
- Fast execution (< 1 second per test)
- No network or file system side effects
- High isolation between tests

### Integration Tests (`tests/integration/`)
Tests for interactions between modules. May use real resources.
- Test module boundaries
- Verify data flow between components
- Test concurrency and race conditions

### E2E Tests (`tests/e2e/`)
Full workflow tests simulating user interactions.
- Test complete user journeys
- Verify system behavior end-to-end
- Use realistic configurations

### Agent Tests (`tests/agents/`)
Comprehensive tests for all 20 agent types using parametrized tests:
- `explore`, `plan`, `code-review`, `general`
- `test-generation`, `documentation`, `refactoring`, `debug`
- `writing`, `communication`, `tutorial`, `diagram`
- `qa-manual`, `research`, `log-analysis`, `performance-analysis`
- `security-audit`, `dependency-analysis`, `migration-planning`, `configuration`

## Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def temp_config_dir(tmp_path):
    """Temporary config directory for testing."""
    ...

@pytest.fixture
def mock_llm_client():
    """Mock LLM client that returns predictable responses."""
    ...

@pytest.fixture
def test_registry():
    """Fresh tool registry for testing."""
    ...
```

## Writing Tests

### Test File Naming
- Unit tests: `test_<module>.py`
- Integration tests: `test_<feature>_integration.py`
- E2E tests: `test_<workflow>_e2e.py`

### Test Class Naming
```python
class TestModuleName:
    """Tests for module functionality."""

class TestClassName:
    """Tests for specific class."""

class TestFeatureIntegration:
    """Integration tests for feature."""
```

### Test Method Naming
```python
def test_<what>_<condition>_<expected_result>(self):
    """Describe what the test verifies."""
    ...

# Examples:
def test_save_api_key_creates_config_dir(self):
def test_execute_unknown_tool_returns_error(self):
def test_cancel_completed_agent_fails(self):
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_operation(self):
    result = await some_async_function()
    assert result.success
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("value1", "result1"),
    ("value2", "result2"),
])
def test_with_multiple_inputs(self, input, expected):
    assert function(input) == expected
```

## Test Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| agents | 90% | 95%+ |
| cli | 85% | 90%+ |
| tools | 90% | 92%+ |
| mcp | 85% | 88%+ |
| skills | 80% | 85%+ |
| context | 85% | 90%+ |
| overall | 85% | 87%+ |

## CI/CD Integration

Tests run automatically on:
- Pull request creation
- Push to main branch
- Nightly builds

Configuration in `.github/workflows/test.yml`.

## Troubleshooting

### Common Issues

**Tests hang or timeout:**
```bash
pytest --timeout=30  # Set per-test timeout
```

**Flaky async tests:**
```bash
pytest --asyncio-mode=auto
```

**Permission errors:**
```bash
# Run tests in a clean environment
pytest --ignore=tests/e2e/
```

**Import errors:**
```bash
# Ensure proper PYTHONPATH
PYTHONPATH=src pytest
```

## Performance Tips

1. Use `pytest-xdist` for parallel execution
2. Run unit tests first with `pytest tests/unit/ -x`
3. Use `--lf` to run last failed tests
4. Use `--ff` to run failures first
5. Use markers to skip slow tests: `pytest -m "not slow"`
