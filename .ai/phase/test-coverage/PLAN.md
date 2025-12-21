# Test Coverage Enhancement: Implementation Plan

**Phase:** test-coverage
**Version Target:** 1.8.0
**Created:** 2025-12-21
**Status:** Planning

---

## Overview

Comprehensive test coverage improvements across all Code-Forge modules to ensure reliability, security, and maintainability. Current test coverage analysis identified 18 critical gaps in security, core functionality, agents, and integrations.

**Current State:**
- 137 test files exist but coverage is uneven
- E2E tests: 100% passing (16/16)
- Critical gaps: CLI setup (0%), SSRF protection (~30%), 17 agents untested
- Missing: Error handling tests, concurrency tests, integration tests

**Goal:**
Achieve comprehensive test coverage by:
- Adding 350-400 new test cases across all priority levels
- Testing all 21 built-in agents
- Validating security-critical code (SSRF, permissions)
- Testing async/concurrent scenarios
- Adding comprehensive error handling tests
- Creating integration and E2E test scenarios

---

## Current State Analysis

### Test Coverage Summary

| Component | Current Coverage | Tests Needed | Priority |
|-----------|-----------------|--------------|----------|
| CLI Setup | 0% | 15+ tests | CRITICAL |
| Dependency Injection | 0% | 10+ tests | CRITICAL |
| SSRF Protection | 30% | 20+ tests | CRITICAL |
| Built-in Agents | 10% | 100+ tests | HIGH |
| Web Search Providers | 20% | 30+ tests | HIGH |
| Session Repository | 50% | 25+ tests | HIGH |
| MCP Transport | 60% | 30+ tests | HIGH |
| HTML Parser | 40% | 15+ tests | MEDIUM |
| Web Cache | 50% | 20+ tests | MEDIUM |
| Config System | 60% | 15+ tests | MEDIUM |
| Workflow System | 65% | 25+ tests | MEDIUM |
| Permission System | 70% | 15+ tests | MEDIUM |

### Critical Gaps Identified

**Security-Critical:**
1. SSRF protection validation
2. Permission system edge cases
3. URL validation and DNS resolution
4. Input validation and sanitization

**Core Functionality:**
5. CLI setup wizard and dependency injection
6. Session repository async operations
7. All 21 built-in agent implementations
8. Web search provider integrations

**Integration Points:**
9. MCP protocol compliance
10. Workflow execution scenarios
11. Configuration loading and merging
12. Error recovery workflows

---

## Implementation Phases

### Phase 1: Critical Security & Setup (Week 1)

**Goal:** Ensure security-critical code is thoroughly tested

#### 1.1 SSRF Protection Tests
**File:** `tests/web/fetch/test_ssrf_protection.py`

**Test Cases:**
- IPv4 private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- IPv6 private ranges (fc00::/7, fe80::/10)
- Loopback addresses (127.0.0.1, ::1)
- Link-local addresses (169.254.0.0/16)
- DNS resolution to private IPs
- IPv6 address validation
- DNS rebinding attack scenarios
- TOCTOU edge cases (documented limitation)
- Malformed IP addresses
- URL host extraction edge cases

**Duration:** 2 days

#### 1.2 CLI Setup Wizard Tests
**File:** `tests/cli/test_setup.py`

**Test Cases:**
- Interactive wizard flow (mocked input)
- API key validation (format, prefix)
- API key save with new file
- API key save with existing file
- File permission handling (chmod 0o600)
- Corrupted JSON recovery
- Missing directory creation
- Permission denied handling
- User cancellation flow
- Config file merging with existing values
- Environment variable override
- Cross-platform file path handling

**Duration:** 2 days

#### 1.3 Dependency Injection Tests
**File:** `tests/cli/test_dependencies.py`

**Test Cases:**
- Factory pattern with default components
- Factory with mock components
- Component initialization failures
- Tool registry integration
- Session manager integration
- Mode manager integration
- get_tool_names() functionality
- Singleton behavior validation
- Lazy initialization
- Error propagation from dependencies

**Duration:** 1 day

**Phase 1 Total:** 5 days

---

### Phase 2: Agent Coverage (Week 2-3)

**Goal:** Test all 21 built-in agents comprehensively

#### 2.1 Agent Infrastructure Tests
**File:** `tests/agents/test_agent_base.py` (enhance existing)

**Test Cases:**
- Agent initialization patterns
- System prompt construction
- Context handling
- Metadata management
- Executor integration
- Result formatting
- Error handling when executor unavailable

**Duration:** 1 day

#### 2.2 Individual Agent Tests
**Files:** `tests/agents/builtin/test_<agent_name>.py` (17 new files)

**Agents to Test:**
1. CommunicationAgent
2. ConfigurationAgent
3. DebugAgent
4. DependencyAnalysisAgent
5. DiagramAgent
6. DocumentationAgent
7. LogAnalysisAgent
8. MigrationPlanningAgent
9. PerformanceAnalysisAgent
10. QAManualAgent
11. RefactoringAgent
12. ResearchAgent
13. SecurityAuditAgent
14. TestGenerationAgent
15. TutorialAgent
16. WritingAgent
17. ReviewAgent (enhance existing)

**Test Template per Agent:**
- Initialization with default config
- Initialization with custom config
- System prompt generation
- Unique instructions validation
- Context preparation
- Execution via AgentExecutor (mocked)
- Result collection and formatting
- Error handling scenarios
- Tool restriction validation (if applicable)

**Duration:** 8 days (17 agents × ~3 tests × 0.5 days)

**Phase 2 Total:** 9 days

---

### Phase 3: Provider & Transport Tests (Week 4)

**Goal:** Test all external integrations comprehensively

#### 3.1 Web Search Provider Tests
**Files:** `tests/web/search/test_<provider>.py`

##### BraveSearchProvider Tests
**File:** `tests/web/search/test_brave.py`

**Test Cases:**
- API call with valid response
- Response parsing (links, titles, snippets)
- Pagination handling
- API error handling (401, 403, 429, 500)
- Network timeout handling
- Malformed response handling
- Missing field handling
- Empty results handling
- Query parameter validation

**Duration:** 1 day

##### GoogleSearchProvider Tests
**File:** `tests/web/search/test_google.py`

**Test Cases:**
- Basic search execution
- Date restriction parameters
- Site search filtering
- Pagination implementation
- Custom search engine ID handling
- API quota errors
- Rate limiting responses
- SSL/TLS validation
- Response field extraction

**Duration:** 1 day

##### DuckDuckGoProvider Tests
**File:** `tests/web/search/test_duckduckgo.py`

**Test Cases:**
- Async thread pool execution
- Library import validation
- Missing library fallback
- Search result parsing
- Thread pool cleanup
- Concurrent search handling
- Timeout handling in threads
- Exception propagation from threads

**Duration:** 1 day

#### 3.2 MCP Transport Tests
**Files:** `tests/mcp/transport/test_<transport>.py` (enhance existing)

##### HTTP Transport Tests
**File:** `tests/mcp/transport/test_http.py`

**Test Cases:**
- Basic HTTP request/response
- Proxy configuration and usage
- SSE (Server-Sent Events) listener
- Health check endpoint
- Connection lifecycle (connect/disconnect)
- Reconnection logic
- Timeout handling
- SSL/TLS certificate validation
- Request ID handling
- Error response handling

**Duration:** 2 days

##### Stdio Transport Tests
**File:** `tests/mcp/transport/test_stdio.py`

**Test Cases:**
- Subprocess spawn and lifecycle
- Message encoding/decoding
- stdin/stdout communication
- Process termination handling
- Zombie process prevention
- Buffer overflow handling
- Encoding errors (UTF-8)
- Process crash recovery
- Timeout on read operations

**Duration:** 2 days

**Phase 3 Total:** 7 days

---

### Phase 4: Async & Concurrency (Week 5)

**Goal:** Test async operations and concurrent scenarios

#### 4.1 Session Repository Async Tests
**File:** `tests/sessions/test_repository_async.py`

**Test Cases:**
- Async context manager protocol
- Thread pool executor operations
- Concurrent reads on same session
- Concurrent writes on same session
- Thread pool executor shutdown
- Async error propagation
- Timeout handling in async operations
- Session summary generation async
- Multiple concurrent repositories
- Lock contention scenarios

**Duration:** 3 days

#### 4.2 Web Cache Concurrency Tests
**File:** `tests/web/test_cache_concurrency.py`

**Test Cases:**
- Thread safety under concurrent access
- Lock acquisition/release
- TTL expiration during concurrent access
- Cache eviction with concurrent operations
- Memory/disk sync under load
- Race conditions in put/get
- Concurrent cleanup operations
- Binary content thread safety
- Cache key collision handling

**Duration:** 2 days

#### 4.3 Workflow Execution Async Tests
**File:** `tests/workflows/test_executor_async.py`

**Test Cases:**
- Parallel step execution
- Dependency resolution with async steps
- Concurrent workflow execution
- Workflow cancellation
- Timeout in workflow steps
- Error propagation in parallel steps
- Resource cleanup after failure
- State consistency during concurrent updates

**Duration:** 2 days

**Phase 4 Total:** 7 days

---

### Phase 5: Error Handling & Edge Cases (Week 6)

**Goal:** Comprehensive error path coverage

#### 5.1 Network Error Scenarios
**File:** `tests/integration/test_network_errors.py`

**Test Cases:**
- Connection timeout
- Read timeout
- DNS resolution failure
- Connection refused
- Network unreachable
- SSL/TLS errors
- Proxy errors
- Rate limiting responses
- Quota exceeded errors
- Retry logic validation
- Exponential backoff validation
- Circuit breaker behavior

**Duration:** 2 days

#### 5.2 File System Error Scenarios
**File:** `tests/integration/test_filesystem_errors.py`

**Test Cases:**
- Permission denied (read)
- Permission denied (write)
- File not found
- Directory not found
- Disk full
- Corrupted JSON data
- Invalid file encoding
- Symlink handling
- Cross-platform path handling
- Locked file handling
- Large file handling

**Duration:** 2 days

#### 5.3 HTML Parser Edge Cases
**File:** `tests/web/fetch/test_parser_edge_cases.py`

**Test Cases:**
- to_text() method
- to_markdown() method
- Relative link resolution
- Malformed HTML handling
- Missing closing tags
- Nested structures
- Special characters in content
- Empty elements
- Base URL handling
- Encoding detection

**Duration:** 1 day

#### 5.4 Configuration Edge Cases
**File:** `tests/config/test_config_edge_cases.py`

**Test Cases:**
- Multi-source merging priority
- Environment variable override
- Missing required fields
- Invalid field types
- Schema validation
- Default value handling
- Partial configuration
- Circular references
- Include/import handling
- Validation error messages

**Duration:** 2 days

**Phase 5 Total:** 7 days

---

### Phase 6: Integration & E2E Scenarios (Week 7)

**Goal:** End-to-end workflow validation

#### 6.1 Full Setup to Execution E2E
**File:** `tests/e2e/test_full_setup.py`

**Test Cases:**
- Setup wizard to first command
- Session creation and persistence
- Multi-session workflow
- Session recovery after crash
- Permission system integration
- Hook execution integration
- Full workflow with all components

**Duration:** 2 days

#### 6.2 Multi-Agent Workflows E2E
**File:** `tests/e2e/test_multi_agent_workflows.py`

**Test Cases:**
- Sequential agent chaining
- Parallel agent execution
- Conditional agent execution
- Agent context passing
- Workflow state persistence
- Workflow resumption
- Error recovery in workflows

**Duration:** 2 days

#### 6.3 MCP Integration E2E
**File:** `tests/e2e/test_mcp_integration.py`

**Test Cases:**
- Full MCP server lifecycle
- Tool discovery via MCP
- Tool execution via MCP
- Error handling in MCP
- Multiple MCP servers
- MCP server reconnection
- JSON-RPC protocol compliance

**Duration:** 2 days

#### 6.4 Web Search Integration E2E
**File:** `tests/e2e/test_web_search_integration.py`

**Test Cases:**
- Search provider selection
- Search result processing
- Content fetching from results
- HTML parsing pipeline
- Cache integration
- Error recovery in search
- Multiple search providers

**Duration:** 1 day

**Phase 6 Total:** 7 days

---

### Phase 7: Documentation & Metrics (Week 8)

**Goal:** Test documentation and coverage reporting

#### 7.1 Test Documentation
**Tasks:**
- Document test strategy in `tests/README.md`
- Add docstrings to all test cases
- Create test data fixtures documentation
- Document mock patterns and utilities
- Create testing best practices guide

**Duration:** 2 days

#### 7.2 Coverage Analysis
**Tasks:**
- Run coverage.py on entire codebase
- Generate HTML coverage reports
- Identify remaining gaps
- Create coverage improvement plan
- Set up CI coverage tracking

**Duration:** 1 day

#### 7.3 Performance Benchmarks
**File:** `tests/performance/benchmarks.py`

**Test Cases:**
- Workflow execution benchmarks
- Tool execution benchmarks
- Session load benchmarks
- Cache performance benchmarks
- Parser performance benchmarks

**Duration:** 2 days

#### 7.4 Final Integration
**Tasks:**
- Update CHANGELOG.md
- Update version to 1.8.0
- Create release notes
- Update UNDONE.md
- Mark FEAT-004 complete

**Duration:** 1 day

**Phase 7 Total:** 6 days

---

## Architecture

### Test Organization

```
tests/
├── unit/                           # Unit tests (isolated)
│   ├── agents/
│   │   ├── builtin/
│   │   │   ├── test_communication.py         [NEW]
│   │   │   ├── test_configuration.py         [NEW]
│   │   │   ├── test_debug.py                 [NEW]
│   │   │   ├── test_dependency_analysis.py   [NEW]
│   │   │   ├── test_diagram.py               [NEW]
│   │   │   ├── test_documentation.py         [NEW]
│   │   │   ├── test_log_analysis.py          [NEW]
│   │   │   ├── test_migration_planning.py    [NEW]
│   │   │   ├── test_performance_analysis.py  [NEW]
│   │   │   ├── test_qa_manual.py             [NEW]
│   │   │   ├── test_refactoring.py           [NEW]
│   │   │   ├── test_research.py              [NEW]
│   │   │   ├── test_security_audit.py        [NEW]
│   │   │   ├── test_test_generation.py       [NEW]
│   │   │   ├── test_tutorial.py              [NEW]
│   │   │   └── test_writing.py               [NEW]
│   ├── cli/
│   │   ├── test_setup.py                     [NEW]
│   │   └── test_dependencies.py              [NEW]
│   ├── config/
│   │   └── test_config_edge_cases.py         [NEW]
│   ├── sessions/
│   │   └── test_repository_async.py          [NEW]
│   └── web/
│       ├── fetch/
│       │   ├── test_ssrf_protection.py       [NEW]
│       │   └── test_parser_edge_cases.py     [NEW]
│       ├── search/
│       │   ├── test_brave.py                 [NEW]
│       │   ├── test_google.py                [NEW]
│       │   └── test_duckduckgo.py            [NEW]
│       └── test_cache_concurrency.py         [NEW]
├── integration/                    # Integration tests
│   ├── test_network_errors.py                [NEW]
│   └── test_filesystem_errors.py             [NEW]
├── e2e/                           # End-to-end tests
│   ├── test_full_setup.py                    [NEW]
│   ├── test_multi_agent_workflows.py         [NEW]
│   ├── test_mcp_integration.py               [NEW]
│   └── test_web_search_integration.py        [NEW]
├── performance/                    # Performance tests
│   └── benchmarks.py                         [NEW]
└── README.md                                 [NEW]
```

### Test Utilities

```
tests/
├── conftest.py                     # Global fixtures (enhance)
├── fixtures/
│   ├── agents.py                             [NEW]
│   ├── network.py                            [NEW]
│   ├── filesystem.py                         [NEW]
│   └── workflows.py                          [NEW]
├── mocks/
│   ├── llm_responses.py                      [NEW]
│   ├── network_responses.py                  [NEW]
│   └── file_system.py                        [NEW]
└── utils/
    ├── assertions.py                         [NEW]
    ├── factories.py                          [NEW]
    └── helpers.py                            [NEW]
```

---

## Testing Patterns

### Pattern 1: Mock External Dependencies

```python
@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for agent tests."""
    with patch('code_forge.llm.provider.LLMProvider') as mock:
        mock.return_value.complete.return_value = CompletionResponse(...)
        yield mock

def test_agent_execution(mock_llm_provider):
    agent = CodeReviewAgent()
    result = agent.execute(context)
    assert result.success
    mock_llm_provider.complete.assert_called_once()
```

### Pattern 2: Async Test Fixtures

```python
@pytest.fixture
async def async_session_manager():
    """Async session manager fixture."""
    manager = SessionRepository()
    async with manager:
        yield manager

@pytest.mark.asyncio
async def test_concurrent_access(async_session_manager):
    # Test concurrent operations
    results = await asyncio.gather(
        async_session_manager.get("s1"),
        async_session_manager.get("s2"),
    )
    assert len(results) == 2
```

### Pattern 3: Parameterized Security Tests

```python
@pytest.mark.parametrize("ip_address,expected", [
    ("10.0.0.1", True),           # Private
    ("172.16.0.1", True),         # Private
    ("192.168.1.1", True),        # Private
    ("8.8.8.8", False),           # Public
    ("127.0.0.1", True),          # Loopback
    ("::1", True),                # IPv6 loopback
    ("fc00::1", True),            # IPv6 private
])
def test_is_private_ip(ip_address, expected):
    assert is_private_ip(ip_address) == expected
```

### Pattern 4: Integration Test Helpers

```python
@contextmanager
def temp_forge_environment():
    """Create temporary Code-Forge environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up config, sessions, etc.
        yield ForgeEnvironment(tmpdir)
        # Cleanup happens automatically

def test_full_workflow():
    with temp_forge_environment() as env:
        # Run full workflow in isolated environment
        result = env.execute_workflow("pr-review")
        assert result.success
```

---

## Success Criteria

### Coverage Metrics

**Target Coverage by Module:**
- CLI Setup: 0% → 90%
- Dependency Injection: 0% → 95%
- SSRF Protection: 30% → 95%
- Built-in Agents: 10% → 85%
- Web Search: 20% → 80%
- Session Repository: 50% → 90%
- MCP Transport: 60% → 85%
- HTML Parser: 40% → 85%
- Web Cache: 50% → 85%
- Overall: ~65% → 85%+

### Quality Gates

**All phases must pass:**
1. ✅ All new tests pass
2. ✅ No regressions in existing tests
3. ✅ Code coverage improves by 20%+
4. ✅ All critical paths tested
5. ✅ All security-critical code tested
6. ✅ Async/concurrent scenarios tested
7. ✅ Error paths comprehensively tested
8. ✅ Integration tests pass
9. ✅ E2E tests pass
10. ✅ Performance benchmarks established

### Documentation Requirements

1. ✅ All test files have module docstrings
2. ✅ All test cases have descriptive docstrings
3. ✅ Testing strategy documented
4. ✅ Mock patterns documented
5. ✅ Coverage reports generated
6. ✅ Known gaps documented

---

## Risks & Mitigations

### Risk 1: Test Execution Time
**Problem:** 350+ new tests might slow down CI/CD
**Mitigation:**
- Parallelize test execution
- Use pytest-xdist for parallel runs
- Separate fast/slow test suites
- Cache test dependencies

### Risk 2: Flaky Async Tests
**Problem:** Async tests can be non-deterministic
**Mitigation:**
- Use pytest-asyncio properly
- Avoid sleep(), use proper await
- Mock time-dependent operations
- Use deterministic test data

### Risk 3: Mock Brittleness
**Problem:** Mocks might not reflect real behavior
**Mitigation:**
- Validate mocks against real implementations
- Use integration tests to catch mock drift
- Document mock assumptions
- Prefer minimal mocking

### Risk 4: Test Maintenance
**Problem:** Large test suites require maintenance
**Mitigation:**
- DRY principle - shared fixtures
- Clear test organization
- Good documentation
- Regular test refactoring

---

## Timeline

**Total Duration:** 8 weeks (48 days)

| Phase | Duration | Completion |
|-------|----------|------------|
| Phase 1: Security & Setup | 5 days | Week 1 |
| Phase 2: Agent Coverage | 9 days | Week 2-3 |
| Phase 3: Providers & Transport | 7 days | Week 4 |
| Phase 4: Async & Concurrency | 7 days | Week 5 |
| Phase 5: Error Handling | 7 days | Week 6 |
| Phase 6: Integration & E2E | 7 days | Week 7 |
| Phase 7: Documentation | 6 days | Week 8 |

**Estimated Test Count:** 350-400 new tests

---

## References

- Code-Forge v1.7.0 - Current production version
- E2E Test Report - `/tests/e2e/E2E_TEST_REPORT_FINAL.md`
- Test Coverage Analysis - Agent exploration results
- Python Testing Best Practices - pytest documentation
- Async Testing - pytest-asyncio patterns
