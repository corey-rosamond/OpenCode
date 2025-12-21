# Test Coverage Enhancement: Test Strategy

**Phase:** test-coverage
**Version Target:** 1.8.0
**Created:** 2025-12-21

---

## Testing Strategy Overview

This document outlines the comprehensive testing approach for achieving 85%+ code coverage across all Code-Forge modules.

---

## Test Categories

### 1. Unit Tests

**Purpose:** Test individual components in isolation

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- Heavy use of mocks
- Focused on single function/class
- Deterministic results

**Coverage Target:** 85% of all code

**Example:**
```python
def test_is_private_ip_detects_private_ipv4():
    """Unit test for SSRF protection."""
    assert is_private_ip("10.0.0.1") == True
    assert is_private_ip("192.168.1.1") == True
    assert is_private_ip("8.8.8.8") == False
```

---

### 2. Integration Tests

**Purpose:** Test component interactions

**Characteristics:**
- Moderate execution time (1-5 seconds)
- Real internal components
- Mock only external services
- Test data flow between modules
- Validate integration points

**Coverage Target:** All integration points

**Example:**
```python
@pytest.mark.asyncio
async def test_session_repository_with_real_storage():
    """Integration test for session persistence."""
    repo = SessionRepository()
    session = Session(title="Test")
    await repo.save(session)

    loaded = await repo.get(session.id)
    assert loaded.title == "Test"
```

---

### 3. End-to-End (E2E) Tests

**Purpose:** Test complete user workflows

**Characteristics:**
- Slower execution (5-30 seconds)
- Full application stack
- Mock only external APIs (LLM, web)
- Simulate real user scenarios
- Validate complete features

**Coverage Target:** All critical user paths

**Example:**
```python
def test_full_pr_review_workflow(forge_env):
    """E2E test for PR review workflow."""
    # Setup
    result = forge_env.run("setup")

    # Execute workflow
    result = forge_env.run("/workflow run pr-review")

    # Verify
    assert result.success
    assert "code review" in result.output.lower()
```

---

### 4. Performance Tests

**Purpose:** Establish performance baselines

**Characteristics:**
- Measure execution time
- Monitor resource usage
- Detect regressions
- Benchmark comparisons
- Stress testing

**Coverage Target:** All performance-critical paths

**Example:**
```python
def test_workflow_execution_performance(benchmark):
    """Benchmark workflow execution time."""
    result = benchmark(execute_workflow, "simple-workflow")
    assert result.duration < 0.1  # < 100ms
```

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                          # Unit tests (isolated)
│   ├── agents/
│   │   ├── builtin/
│   │   │   ├── test_code_review.py
│   │   │   ├── test_test_generation.py
│   │   │   └── ... (17 more agent tests)
│   │   ├── test_executor.py
│   │   └── test_manager.py
│   ├── cli/
│   │   ├── test_setup.py          [NEW]
│   │   └── test_dependencies.py   [NEW]
│   ├── config/
│   │   └── test_edge_cases.py     [NEW]
│   ├── sessions/
│   │   └── test_repository_async.py [NEW]
│   └── web/
│       ├── fetch/
│       │   ├── test_ssrf_protection.py [NEW]
│       │   └── test_parser_edge_cases.py [NEW]
│       ├── search/
│       │   ├── test_brave.py      [NEW]
│       │   ├── test_google.py     [NEW]
│       │   └── test_duckduckgo.py [NEW]
│       └── test_cache_concurrency.py [NEW]
│
├── integration/                   # Integration tests
│   ├── test_network_errors.py     [NEW]
│   ├── test_filesystem_errors.py  [NEW]
│   └── test_component_integration.py
│
├── e2e/                           # End-to-end tests
│   ├── test_smoke.py              (existing - 16 tests)
│   ├── test_full_setup.py         [NEW]
│   ├── test_multi_agent_workflows.py [NEW]
│   ├── test_mcp_integration.py    [NEW]
│   └── test_web_search_integration.py [NEW]
│
├── performance/                    # Performance tests
│   └── benchmarks.py              [NEW]
│
├── fixtures/                      # Shared test data
│   ├── agents.py                  [NEW]
│   ├── network.py                 [NEW]
│   ├── filesystem.py              [NEW]
│   └── workflows.py               [NEW]
│
├── mocks/                         # Mock implementations
│   ├── llm_responses.py           [NEW]
│   ├── network_responses.py       [NEW]
│   └── file_system.py             [NEW]
│
├── utils/                         # Test utilities
│   ├── assertions.py              [NEW]
│   ├── factories.py               [NEW]
│   └── helpers.py                 [NEW]
│
├── conftest.py                    # Global pytest config
└── README.md                      # Testing guide [NEW]
```

---

## Testing Patterns

### Pattern 1: AAA (Arrange-Act-Assert)

```python
def test_agent_execution():
    # Arrange
    agent = CodeReviewAgent()
    context = ExecutionContext(task="Review code")

    # Act
    result = agent.execute(context)

    # Assert
    assert result.success
    assert "review" in result.output.lower()
```

### Pattern 2: Given-When-Then (BDD Style)

```python
def test_ssrf_protection():
    # Given a private IP address
    ip_address = "192.168.1.1"

    # When validation is performed
    is_private = is_private_ip(ip_address)

    # Then it should be classified as private
    assert is_private == True
```

### Pattern 3: Parameterized Tests

```python
@pytest.mark.parametrize("ip,expected", [
    ("10.0.0.1", True),
    ("192.168.1.1", True),
    ("8.8.8.8", False),
    ("127.0.0.1", True),
])
def test_private_ip_detection(ip, expected):
    assert is_private_ip(ip) == expected
```

### Pattern 4: Fixture-Based Setup

```python
@pytest.fixture
def code_review_agent():
    """Provide a configured CodeReviewAgent."""
    return CodeReviewAgent(
        config=AgentConfig(max_tokens=4000)
    )

def test_agent_with_fixture(code_review_agent):
    result = code_review_agent.execute(context)
    assert result.success
```

### Pattern 5: Mock External Dependencies

```python
@patch('code_forge.llm.provider.LLMProvider')
def test_agent_without_real_llm(mock_provider):
    # Configure mock
    mock_provider.return_value.complete.return_value = CompletionResponse(
        content="Code review complete"
    )

    # Test with mock
    agent = CodeReviewAgent()
    result = agent.execute(context)

    assert result.success
    mock_provider.return_value.complete.assert_called_once()
```

### Pattern 6: Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    repo = SessionRepository()
    async with repo:
        session = await repo.get("session_id")
        assert session is not None
```

### Pattern 7: Exception Testing

```python
def test_error_handling():
    """Test that appropriate errors are raised."""
    with pytest.raises(ValueError, match="Invalid IP address"):
        is_private_ip("not-an-ip")
```

### Pattern 8: Context Manager Testing

```python
def test_context_manager():
    """Test resource cleanup."""
    with SessionRepository() as repo:
        # Use repository
        session = repo.get("id")

    # Verify cleanup
    assert repo._thread_pool.shutdown_called
```

---

## Mock Strategies

### HTTP Mocking (responses library)

```python
import responses

@responses.activate
def test_brave_search():
    responses.add(
        responses.GET,
        "https://api.search.brave.com/res/v1/web/search",
        json={"results": [{"title": "Result 1"}]},
        status=200
    )

    provider = BraveSearchProvider(api_key="test")
    results = provider.search("query")
    assert len(results) == 1
```

### Async HTTP Mocking (aioresponses)

```python
from aioresponses import aioresponses

@pytest.mark.asyncio
@aioresponses()
async def test_async_fetch(mock_aiohttp):
    mock_aiohttp.get(
        "https://example.com",
        payload={"data": "test"}
    )

    fetcher = URLFetcher()
    result = await fetcher.fetch("https://example.com")
    assert result == {"data": "test"}
```

### File System Mocking

```python
from unittest.mock import mock_open, patch

def test_file_read():
    mock_data = "test content"
    with patch("builtins.open", mock_open(read_data=mock_data)):
        content = read_file("test.txt")
        assert content == mock_data
```

### LLM Mocking

```python
@pytest.fixture
def mock_llm():
    with patch('code_forge.llm.provider.LLMProvider') as mock:
        mock.return_value.complete.return_value = CompletionResponse(
            content="Mocked response",
            model="claude-3-sonnet",
            usage={"tokens": 100}
        )
        yield mock
```

---

## Coverage Measurement

### Running Coverage

```bash
# Basic coverage
pytest --cov=src/code_forge

# With HTML report
pytest --cov=src/code_forge --cov-report=html

# With terminal report
pytest --cov=src/code_forge --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=src/code_forge --cov-fail-under=85
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/code_forge"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Coverage Targets by Module

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| cli/setup.py | 0% | 90% | Critical |
| web/fetch/fetcher.py | 30% | 95% | Critical |
| agents/builtin/* | 10% | 85% | High |
| web/search/* | 20% | 80% | High |
| sessions/repository.py | 50% | 90% | High |
| mcp/transport/* | 60% | 85% | Medium |
| workflows/* | 65% | 85% | Medium |

---

## Test Execution

### Running All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/cli/test_setup.py

# Run specific test
pytest tests/unit/cli/test_setup.py::test_setup_wizard
```

### Running by Category

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/

# Performance tests only
pytest tests/performance/
```

### Running by Marker

```bash
# Run tests marked as slow
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run only security tests
pytest -m security

# Run async tests only
pytest -m asyncio
```

### Parallel Execution

```bash
# Auto-detect CPU count
pytest -n auto

# Use 4 workers
pytest -n 4

# Distribute by file
pytest -n auto --dist loadfile
```

---

## Test Data Management

### Fixtures

```python
# Global fixtures in conftest.py
@pytest.fixture
def temp_forge_env(tmp_path):
    """Create temporary Code-Forge environment."""
    config_dir = tmp_path / ".forge"
    config_dir.mkdir()
    return ForgeEnvironment(config_dir)

@pytest.fixture
def sample_code():
    """Provide sample code for testing."""
    return '''
    def hello(name):
        return f"Hello, {name}!"
    '''
```

### Factories

```python
# tests/utils/factories.py
class AgentFactory:
    @staticmethod
    def create_code_review_agent(**kwargs):
        defaults = {
            "config": AgentConfig(max_tokens=4000)
        }
        defaults.update(kwargs)
        return CodeReviewAgent(**defaults)

class SessionFactory:
    @staticmethod
    def create_session(**kwargs):
        defaults = {
            "title": "Test Session",
            "created_at": datetime.now()
        }
        defaults.update(kwargs)
        return Session(**defaults)
```

### Test Data Files

```
tests/data/
├── sample_html/
│   ├── valid.html
│   ├── malformed.html
│   └── with_links.html
├── sample_code/
│   ├── python/
│   │   ├── simple.py
│   │   └── complex.py
│   └── javascript/
│       └── example.js
├── sample_workflows/
│   ├── sequential.yaml
│   ├── parallel.yaml
│   └── conditional.yaml
└── sample_configs/
    ├── minimal.json
    └── complete.json
```

---

## Continuous Integration

### CI Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev

      - name: Run tests with coverage
        run: |
          poetry run pytest --cov=src/code_forge --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

---

## Quality Gates

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Run fast tests
        entry: pytest tests/unit -m "not slow"
        language: system
        pass_filenames: false
        always_run: true
```

### Git Hooks

```bash
# .git/hooks/pre-push
#!/bin/bash
echo "Running tests before push..."
pytest --cov=src/code_forge --cov-fail-under=85
if [ $? -ne 0 ]; then
    echo "Tests failed. Push aborted."
    exit 1
fi
```

---

## Test Metrics

### Success Criteria

- ✅ All tests pass (100% pass rate)
- ✅ Coverage ≥ 85%
- ✅ No test takes > 5 seconds (unit tests)
- ✅ No flaky tests (consistent results)
- ✅ All critical paths tested

### Tracking

```bash
# Generate coverage report
pytest --cov=src/code_forge --cov-report=term-missing

# Generate HTML report
pytest --cov=src/code_forge --cov-report=html
open htmlcov/index.html

# Generate JSON report
pytest --json-report --json-report-file=report.json
```

---

## Testing Best Practices

### DO

- ✅ Write tests before fixing bugs
- ✅ Use descriptive test names
- ✅ Test one thing per test
- ✅ Use fixtures for common setup
- ✅ Mock external dependencies
- ✅ Clean up resources
- ✅ Document complex test scenarios

### DON'T

- ❌ Test implementation details
- ❌ Use sleep() in tests
- ❌ Depend on test execution order
- ❌ Leave commented-out tests
- ❌ Ignore flaky tests
- ❌ Skip writing tests for "simple" code
- ❌ Make real API calls in tests

---

## Summary

**Total New Tests:** 350-400
**Test Categories:** Unit, Integration, E2E, Performance
**Coverage Target:** 85%+
**Execution Time:** < 5 minutes (full suite)
**Success Criteria:** All tests pass, no regressions, comprehensive coverage
