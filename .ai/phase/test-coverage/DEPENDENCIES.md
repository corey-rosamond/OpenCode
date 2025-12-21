# Test Coverage Enhancement: Dependencies

**Phase:** test-coverage
**Version Target:** 1.8.0
**Created:** 2025-12-21

---

## External Dependencies

### Required for Implementation

No new production dependencies required. All testing dependencies already exist in project.

---

## Development Dependencies

### Existing (Already in pyproject.toml)

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^9.0.0"
pytest-asyncio = "^1.3.0"
pytest-cov = "^6.0.0"
pytest-mock = "^3.14.0"
```

### Recommended Additions

```toml
[tool.poetry.group.dev.dependencies]
# Parallel test execution
pytest-xdist = "^3.5.0"

# Property-based testing
hypothesis = "^6.92.0"

# Test fixtures and factories
pytest-factoryboy = "^2.7.0"
faker = "^22.0.0"

# Async testing utilities
pytest-timeout = "^2.2.0"
trio = "^0.24.0"  # Alternative async backend for testing

# Code coverage enhancement
coverage = { extras = ["toml"], version = "^7.4.0" }

# Mock HTTP requests
responses = "^0.24.0"
aioresponses = "^0.7.6"

# Test reporting
pytest-html = "^4.1.1"
pytest-json-report = "^1.5.0"
```

---

## Internal Dependencies

### Modules Required for Testing

All tests depend on core Code-Forge modules:

```python
# Core infrastructure
from code_forge.core import (
    CodeForgeError,
    ToolError,
    SessionError,
    ConfigError,
)

# Agent system
from code_forge.agents import (
    Agent,
    AgentManager,
    AgentExecutor,
    AgentResult,
    AgentConfig,
)

# Agent types
from code_forge.agents.builtin import (
    CodeReviewAgent,
    TestGenerationAgent,
    DocumentationAgent,
    DebugAgent,
    # ... all 21 agents
)

# Tools
from code_forge.tools import (
    ToolRegistry,
    BaseTool,
    ToolResult,
)

# Sessions
from code_forge.sessions import (
    SessionManager,
    SessionRepository,
    SessionStorage,
    Session,
)

# Web modules
from code_forge.web.fetch import (
    URLFetcher,
    HTMLParser,
)
from code_forge.web.search import (
    BraveSearchProvider,
    GoogleSearchProvider,
    DuckDuckGoProvider,
)
from code_forge.web.cache import WebCache

# MCP
from code_forge.mcp.protocol import (
    MCPRequest,
    MCPResponse,
    MCPError,
)
from code_forge.mcp.transport import (
    HTTPTransport,
    StdioTransport,
)

# Workflows
from code_forge.workflows import (
    WorkflowExecutor,
    WorkflowDefinition,
    WorkflowState,
)

# Configuration
from code_forge.config import (
    ConfigLoader,
    Config,
)

# CLI
from code_forge.cli.setup import (
    run_setup_wizard,
    save_api_key,
    check_api_key_configured,
)
from code_forge.cli.dependencies import Dependencies

# Permissions
from code_forge.permissions import (
    PermissionChecker,
    PermissionConfig,
)
```

---

## Test Infrastructure Dependencies

### Test Fixtures

```python
# Global fixtures (tests/conftest.py)
- temp_dir
- temp_project
- sample_python_project
- git_project
- forge_runner
- tool_registry_with_tools
- execution_context
- session_manager
- e2e_forge_config

# New fixtures required:
- mock_llm_provider
- mock_http_responses
- mock_file_system
- async_session_manager
- workflow_definition
- agent_factory
- mcp_server_mock
```

### Mock Objects

```python
# Network mocks
- MockHTTPResponse
- MockSearchResults
- MockMCPServer

# LLM mocks
- MockLLMProvider
- MockCompletionResponse
- MockStreamingResponse

# File system mocks
- MockFileSystem
- MockPermissions
- MockEnv

# Agent mocks
- MockAgentExecutor
- MockAgentResult
```

---

## Dependency Graph

### Phase 1: Critical Security & Setup

```
CLI Setup Tests
├── code_forge.cli.setup
├── code_forge.config (ConfigLoader)
├── mock: file system operations
└── mock: user input prompts

SSRF Protection Tests
├── code_forge.web.fetch.fetcher
├── Python: ipaddress module
├── Python: socket module
└── mock: DNS resolution

Dependency Injection Tests
├── code_forge.cli.dependencies
├── code_forge.tools (ToolRegistry)
├── code_forge.sessions (SessionManager)
└── code_forge.modes (ModeManager)
```

### Phase 2: Agent Coverage

```
Agent Tests (×21)
├── code_forge.agents.builtin.<agent>
├── code_forge.agents.executor (AgentExecutor)
├── code_forge.agents.manager (AgentManager)
├── mock: LLMProvider
└── mock: Tool execution
```

### Phase 3: Provider & Transport Tests

```
Web Search Provider Tests
├── code_forge.web.search.<provider>
├── mock: HTTP responses
├── mock: API authentication
└── mock: Network errors

MCP Transport Tests
├── code_forge.mcp.transport.<transport>
├── code_forge.mcp.protocol
├── mock: HTTP connections
├── mock: subprocess
└── mock: stdio streams
```

### Phase 4: Async & Concurrency

```
Async Tests
├── pytest-asyncio
├── asyncio standard library
├── concurrent.futures (thread pools)
└── threading (locks, events)

Session Repository Async
├── code_forge.sessions.repository
├── aiofiles
└── concurrent.futures.ThreadPoolExecutor

Cache Concurrency
├── code_forge.web.cache
├── threading.Lock
└── pytest-xdist (parallel execution)
```

### Phase 5: Error Handling

```
Error Tests
├── All code_forge modules
├── mock: Network errors (timeout, connection refused)
├── mock: File system errors (permission, not found)
├── mock: Async errors (cancellation, timeout)
└── pytest.raises context manager
```

### Phase 6: Integration & E2E

```
Integration Tests
├── All code_forge modules (real objects)
├── Real file system (temp directories)
├── Mock: External APIs only
└── Real: All internal components

E2E Tests
├── Complete application stack
├── Real configuration
├── Real session management
├── Mock: Only LLM API calls
└── Real: Everything else
```

---

## Build-Time Dependencies

### Coverage Collection

```bash
# Install coverage tools
pip install pytest-cov coverage[toml]

# Run tests with coverage
pytest --cov=src/code_forge --cov-report=html --cov-report=term
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto  # Auto-detect CPU count
pytest -n 4     # Use 4 workers
```

### HTML Reports

```bash
# Install pytest-html
pip install pytest-html

# Generate HTML test report
pytest --html=reports/test_report.html --self-contained-html
```

---

## Version Compatibility

### Python Version
- **Minimum:** Python 3.10
- **Tested:** Python 3.10, 3.11, 3.12
- **Recommended:** Python 3.12

### pytest Version
- **Minimum:** pytest 9.0.0
- **Features Required:**
  - Async test support
  - Fixtures
  - Parametrization
  - Markers

### pytest-asyncio Version
- **Minimum:** pytest-asyncio 1.3.0
- **Features Required:**
  - @pytest.mark.asyncio
  - Async fixtures
  - Event loop handling

---

## Dependency Installation

### Development Setup

```bash
# Install all development dependencies
poetry install --with dev

# Or with pip (if not using poetry)
pip install -e ".[dev]"
```

### CI/CD Setup

```bash
# Minimal dependencies for CI
poetry install --with dev --no-root

# Run tests
poetry run pytest
```

### Optional Dependencies

```bash
# For property-based testing
poetry add --group dev hypothesis

# For parallel execution
poetry add --group dev pytest-xdist

# For HTTP mocking
poetry add --group dev responses aioresponses

# For better test reporting
poetry add --group dev pytest-html pytest-json-report
```

---

## Circular Dependency Prevention

### Test Isolation

Tests must not create circular dependencies:

```python
# ✅ Good: Tests import from src
from code_forge.agents import Agent
from code_forge.tools import BaseTool

# ❌ Bad: src imports from tests
# (Never do this)
```

### Mock Strategy

Use mocks to break dependencies:

```python
# ✅ Good: Mock external dependencies
@patch('code_forge.llm.provider.LLMProvider')
def test_agent(mock_provider):
    agent = Agent()
    # Test in isolation

# ❌ Bad: Real LLM calls in tests
def test_agent():
    agent = Agent()
    agent.execute()  # Makes real API call
```

---

## Risk Mitigation

### Dependency Version Locking

**Risk:** Test failures due to dependency updates
**Mitigation:** Use `poetry.lock` to pin versions

### Mock Drift

**Risk:** Mocks diverge from real implementations
**Mitigation:**
- Integration tests validate real behavior
- Mock validation tests
- Regular mock review

### Test Data Dependencies

**Risk:** Tests depend on specific external data
**Mitigation:**
- Bundle test fixtures
- Generate test data dynamically
- Use faker for realistic data

---

## Dependencies Summary

| Category | Count | Status |
|----------|-------|--------|
| New Production Dependencies | 0 | N/A |
| Existing Dev Dependencies | 4 | ✅ Installed |
| Recommended Dev Dependencies | 10 | 📦 Optional |
| Internal Module Dependencies | 50+ | ✅ Available |
| Test Fixtures Required | 20+ | 🔨 To Create |
| Mock Objects Required | 15+ | 🔨 To Create |

**Total External Dependencies:** 0 new (all testing tools already available)

**Status:** ✅ All required dependencies available, no blockers
