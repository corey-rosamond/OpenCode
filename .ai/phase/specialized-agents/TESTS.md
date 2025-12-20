# Specialized Task Agents: Test Strategy

**Phase:** specialized-agents
**Version Target:** 1.6.0
**Created:** 2025-12-21

Comprehensive test strategy for all 16 new specialized agents.

---

## 1. Test Philosophy

### 1.1 Test-Driven Development (TDD)
- Write tests **before** implementation where possible
- Red-Green-Refactor cycle
- Tests define expected behavior

### 1.2 Behavior-Driven Development (BDD)
- Tests derived from GHERKIN.md scenarios
- User-centric test descriptions
- Clear Given/When/Then structure

### 1.3 Coverage Goals
- **Minimum:** 90% code coverage
- **Target:** 95% code coverage
- **Critical paths:** 100% coverage

---

## 2. Test Pyramid

```
         /\
        /  \       E2E Tests (5%)
       /____\      - Full system integration
      /      \     - Real scenarios
     /________\    Integration Tests (25%)
    /          \   - Component interactions
   /____________\  - Tool/permission/hook integration
  /              \
 /________________\ Unit Tests (70%)
                    - Agent type definitions
                    - Agent implementations
                    - Individual methods
```

---

## 3. Test Categories

### 3.1 Unit Tests (70% of tests)

**Scope:** Individual components in isolation
**Tools:** pytest, pytest-mock
**Mocking:** Heavy mocking of dependencies

**Test Files:**
```
tests/unit/agents/
├── test_types.py                           # Registry tests
└── builtin/
    ├── test_test_generation.py
    ├── test_documentation.py
    ├── test_refactoring.py
    ├── test_debug.py
    ├── test_writing.py
    ├── test_communication.py
    ├── test_tutorial.py
    ├── test_diagram.py
    ├── test_qa_manual.py
    ├── test_research.py
    ├── test_log_analysis.py
    ├── test_performance_analysis.py
    ├── test_security_audit.py
    ├── test_dependency_analysis.py
    ├── test_migration_planning.py
    └── test_configuration.py
```

### 3.2 Integration Tests (25% of tests)

**Scope:** Multiple components working together
**Tools:** pytest, pytest-asyncio
**Mocking:** Minimal mocking, real components

**Test Files:**
```
tests/integration/
└── test_all_specialized_agents.py
```

### 3.3 End-to-End Tests (5% of tests)

**Scope:** Full system with real scenarios
**Tools:** pytest, real LLM calls (if configured)
**Mocking:** Only external services

**Test Files:**
```
tests/e2e/
└── test_agent_scenarios.py
```

---

## 4. Unit Test Strategy

### 4.1 Agent Type Registry Tests
**File:** `tests/unit/agents/test_types.py`

#### Test Cases:

**Registry Initialization:**
```python
def test_registry_singleton():
    """Registry returns same instance"""

def test_registry_initializes_with_builtins():
    """Registry contains all 20 agent types"""

def test_registry_contains_all_new_types():
    """Registry contains all 16 new types"""
```

**Type Definitions:**
```python
# For EACH of 16 new agent types:
def test_{agent_type}_exists():
    """Type {agent_type} is registered"""

def test_{agent_type}_has_description():
    """Type {agent_type} has non-empty description"""

def test_{agent_type}_has_prompt():
    """Type {agent_type} has prompt template"""

def test_{agent_type}_has_correct_tools():
    """Type {agent_type} has expected default tools"""

def test_{agent_type}_has_resource_limits():
    """Type {agent_type} has appropriate limits"""
```

**Registry Operations:**
```python
def test_get_existing_type_returns_definition():
    """get() returns definition for existing type"""

def test_get_nonexistent_type_returns_none():
    """get() returns None for unknown type"""

def test_list_types_returns_all_20():
    """list_types() returns exactly 20 types"""

def test_exists_returns_true_for_existing():
    """exists() returns True for registered types"""

def test_exists_returns_false_for_nonexistent():
    """exists() returns False for unknown types"""

def test_duplicate_registration_raises_error():
    """Registering duplicate type raises ValueError"""

def test_unregister_removes_type():
    """unregister() removes type from registry"""
```

### 4.2 Agent Implementation Tests
**Files:** `tests/unit/agents/builtin/test_{agent_name}.py`

#### Template for Each Agent:

```python
import pytest
from code_forge.agents.builtin.{agent_name} import {AgentName}Agent
from code_forge.agents.base import AgentConfig, AgentContext, AgentState

class Test{AgentName}Agent:
    """Tests for {AgentName}Agent"""

    # Initialization
    def test_initialization(self):
        """Agent initializes correctly"""
        config = AgentConfig.for_type("{agent-type}")
        agent = {AgentName}Agent(
            task="Test task",
            config=config
        )
        assert agent.agent_type == "{agent-type}"
        assert agent.state == AgentState.PENDING
        assert agent.task == "Test task"

    def test_agent_type_property(self):
        """agent_type property returns correct value"""
        config = AgentConfig.for_type("{agent-type}")
        agent = {AgentName}Agent(task="Test", config=config)
        assert agent.agent_type == "{agent-type}"

    # Configuration
    def test_config_from_factory(self):
        """AgentConfig.for_type() creates correct config"""
        config = AgentConfig.for_type("{agent-type}")
        assert config.agent_type == "{agent-type}"
        assert config.tools == [{expected_tools}]
        assert config.limits.max_tokens == {expected_tokens}
        assert config.limits.max_time_seconds == {expected_time}

    def test_config_override(self):
        """Config values can be overridden"""
        config = AgentConfig.for_type(
            "{agent-type}",
            max_tokens=100000
        )
        assert config.limits.max_tokens == 100000

    # State Management
    @pytest.mark.asyncio
    async def test_execute_sets_running_state(self, mocker):
        """execute() transitions to running state"""
        config = AgentConfig.for_type("{agent-type}")
        agent = {AgentName}Agent(task="Test", config=config)

        # Mock execute to avoid real LLM calls
        mocker.patch.object(agent, '_execute_impl', return_value=...)

        await agent.execute()
        # Verify state transitions

    @pytest.mark.asyncio
    async def test_successful_execution_sets_completed(self, mocker):
        """Successful execution sets completed state"""
        # Test implementation

    @pytest.mark.asyncio
    async def test_failed_execution_sets_failed(self, mocker):
        """Failed execution sets failed state"""
        # Test implementation

    # Tool Access
    def test_allowed_tools_specified(self):
        """Agent has correct allowed tools"""
        config = AgentConfig.for_type("{agent-type}")
        assert set(config.tools) == set([{expected_tools}])

    def test_restricted_tools_denied(self, mocker):
        """Restricted tools raise error"""
        # Test that tools not in default_tools are denied

    # Resource Limits
    @pytest.mark.asyncio
    async def test_respects_token_limit(self, mocker):
        """Agent stops at token limit"""
        # Test token limit enforcement

    @pytest.mark.asyncio
    async def test_respects_time_limit(self, mocker):
        """Agent stops at time limit"""
        # Test time limit enforcement

    # Cancellation
    def test_cancel_pending_agent(self):
        """Can cancel pending agent"""
        config = AgentConfig.for_type("{agent-type}")
        agent = {AgentName}Agent(task="Test", config=config)
        result = agent.cancel()
        assert result is True
        assert agent.is_cancelled

    def test_cannot_cancel_completed_agent(self):
        """Cannot cancel completed agent"""
        # Test cancellation of completed agent

    # Result
    @pytest.mark.asyncio
    async def test_result_structure(self, mocker):
        """Result has expected structure"""
        # Test AgentResult structure

    @pytest.mark.asyncio
    async def test_result_serialization(self, mocker):
        """Result can be serialized to dict"""
        # Test to_dict() method

    # Error Handling
    @pytest.mark.asyncio
    async def test_handles_tool_error(self, mocker):
        """Agent handles tool execution errors"""
        # Test error handling

    @pytest.mark.asyncio
    async def test_handles_llm_error(self, mocker):
        """Agent handles LLM API errors"""
        # Test LLM error handling
```

### 4.3 Mocking Strategy

**Mock LLM Responses:**
```python
@pytest.fixture
def mock_llm_response(mocker):
    """Mock LLM to return fixed response"""
    mock = mocker.patch('code_forge.langchain.llm.OpenRouterLLM')
    mock.return_value.agenerate.return_value = MagicMock(
        generations=[[MagicMock(text="Mocked response")]]
    )
    return mock
```

**Mock Tool Execution:**
```python
@pytest.fixture
def mock_tool_executor(mocker):
    """Mock tool execution"""
    mock = mocker.patch('code_forge.tools.executor.ToolExecutor')
    mock.return_value.execute.return_value = ToolResult(
        success=True,
        output="Mocked output"
    )
    return mock
```

---

## 5. Integration Test Strategy

### 5.1 Test File Structure
**File:** `tests/integration/test_all_specialized_agents.py`

### 5.2 Integration Test Cases

**Agent-Tool Integration:**
```python
@pytest.mark.asyncio
async def test_agent_executes_allowed_tools():
    """Agents can execute allowed tools"""
    # For each agent type, test tool execution

@pytest.mark.asyncio
async def test_agent_denied_restricted_tools():
    """Agents cannot execute restricted tools"""
    # Verify tool restrictions enforced
```

**Agent-Permission Integration:**
```python
@pytest.mark.asyncio
async def test_agent_respects_permissions():
    """Agents respect permission system"""
    # Configure permissions, verify agent respects them

@pytest.mark.asyncio
async def test_agent_prompts_user_for_restricted_op():
    """Agents prompt user for restricted operations"""
    # Test permission prompting
```

**Agent-Hook Integration:**
```python
@pytest.mark.asyncio
async def test_agent_fires_hooks():
    """Agents fire lifecycle hooks"""
    # Configure hooks, verify they fire

@pytest.mark.asyncio
async def test_hook_can_modify_agent_behavior():
    """Hooks can modify agent execution"""
    # Test hook modification
```

**Agent-Session Integration:**
```python
@pytest.mark.asyncio
async def test_agent_messages_recorded_in_session():
    """Agent messages added to session"""
    # Verify session recording

@pytest.mark.asyncio
async def test_agent_results_persisted():
    """Agent results saved to session"""
    # Verify result persistence
```

**Agent-Context Integration:**
```python
@pytest.mark.asyncio
async def test_agent_tracks_token_usage():
    """Agent tracks token consumption"""
    # Verify token tracking

@pytest.mark.asyncio
async def test_agent_enforces_token_limit():
    """Agent stops at token limit"""
    # Verify limit enforcement
```

**Concurrent Execution:**
```python
@pytest.mark.asyncio
async def test_multiple_agents_concurrent():
    """Multiple agents run concurrently without conflicts"""
    # Create and run 5 agents in parallel
    # Verify all complete successfully

@pytest.mark.asyncio
async def test_same_type_multiple_instances():
    """Same agent type runs multiple instances"""
    # Create 3 research agents
    # Run concurrently
    # Verify independence
```

### 5.3 Real Component Integration

Integration tests use **real** components (not mocked):
- Real ToolExecutor
- Real PermissionChecker
- Real HookExecutor
- Real SessionManager
- Real ContextManager

Only LLM calls mocked (unless INTEGRATION_TEST_LLM=true).

---

## 6. End-to-End Test Strategy

### 6.1 Real Scenario Tests
**File:** `tests/e2e/test_agent_scenarios.py`

### 6.2 Scenario Tests

**Coding Agent Scenarios:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_test_generation_agent_creates_tests():
    """test-generation agent creates real test file"""
    # Create sample code file
    # Run agent with task "Generate tests"
    # Verify test file created
    # Verify tests are valid pytest

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_refactoring_agent_removes_duplication():
    """refactoring agent removes duplicate code"""
    # Create files with duplication
    # Run agent with task "Remove duplication"
    # Verify duplication removed
    # Verify behavior preserved
```

**Research Agent Scenarios:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skipif(not has_web_access(), reason="No web access")
async def test_research_agent_compares_technologies():
    """research agent compares technologies"""
    # Run agent with task "Compare X vs Y"
    # Verify research conducted
    # Verify comparison report generated
    # Verify sources included
```

**Security Agent Scenarios:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_security_audit_finds_sql_injection():
    """security-audit agent finds SQL injection"""
    # Create file with SQL injection vulnerability
    # Run agent with task "Security audit"
    # Verify vulnerability detected
    # Verify severity categorized as critical
    # Verify fix suggested
```

### 6.3 E2E Test Markers

```python
# Skip E2E tests by default (slow)
@pytest.mark.e2e

# Skip if no web access
@pytest.mark.skipif(not has_web_access())

# Skip if no LLM API key
@pytest.mark.skipif(not has_llm_api_key())

# Run with: pytest -m e2e
```

---

## 7. Test Coverage Requirements

### 7.1 Code Coverage Targets

| Component | Minimum | Target |
|-----------|---------|--------|
| agents/types.py | 95% | 100% |
| agents/builtin/*.py (each) | 90% | 95% |
| Overall project | 90% | 95% |

### 7.2 Critical Path Coverage

**Must be 100% covered:**
- Agent initialization
- Agent state transitions
- Tool access validation
- Resource limit enforcement
- Error handling

### 7.3 Coverage Measurement

```bash
# Run with coverage
pytest tests/ --cov=src/code_forge/agents --cov-report=html

# View report
open htmlcov/index.html

# Fail if coverage < 90%
pytest tests/ --cov=src/code_forge/agents --cov-fail-under=90
```

---

## 8. Test Organization

### 8.1 Directory Structure

```
tests/
├── unit/
│   └── agents/
│       ├── test_types.py
│       └── builtin/
│           ├── test_test_generation.py
│           ├── test_documentation.py
│           ├── ...
│           └── test_configuration.py
├── integration/
│   └── test_all_specialized_agents.py
├── e2e/
│   └── test_agent_scenarios.py
└── conftest.py                      # Shared fixtures
```

### 8.2 Fixture Organization

**Shared Fixtures (`tests/conftest.py`):**
```python
@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for agents"""
    return tmp_path

@pytest.fixture
def mock_llm():
    """Mock LLM responses"""
    # Implementation

@pytest.fixture
def sample_code_file(temp_workspace):
    """Create sample code file for testing"""
    # Implementation

@pytest.fixture
def sample_log_file(temp_workspace):
    """Create sample log file for testing"""
    # Implementation
```

---

## 9. Test Execution Strategy

### 9.1 Local Development

```bash
# Run all tests
pytest tests/

# Run only unit tests (fast)
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only E2E tests
pytest tests/e2e/ -m e2e

# Run tests for specific agent
pytest tests/unit/agents/builtin/test_research.py

# Run with coverage
pytest tests/ --cov=src/code_forge/agents

# Run in watch mode
pytest-watch tests/
```

### 9.2 CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/unit/ --cov --cov-fail-under=90

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/integration/

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: pytest tests/e2e/ -m e2e
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

---

## 10. Test Data Strategy

### 10.1 Test Data Files

```
tests/fixtures/
├── code_samples/
│   ├── calculator.py              # For test-generation agent
│   ├── undocumented.py            # For documentation agent
│   └── duplicated.py              # For refactoring agent
├── logs/
│   ├── error.log                  # For log-analysis agent
│   └── access.log                 # For log-analysis agent
├── configs/
│   ├── valid.yaml                 # For configuration agent
│   └── invalid.yaml               # For configuration agent
└── security/
    ├── sql_injection.py           # For security-audit agent
    └── xss_vulnerable.py          # For security-audit agent
```

### 10.2 Dynamic Test Data

Generate test data on-the-fly:
```python
@pytest.fixture
def large_log_file(tmp_path):
    """Generate large log file"""
    log_file = tmp_path / "large.log"
    with open(log_file, 'w') as f:
        for i in range(10000):
            f.write(f"[ERROR] Error {i % 10}\n")
    return log_file
```

---

## 11. Test Quality Criteria

### 11.1 Test Quality Checklist

Each test must:
- [ ] Have clear, descriptive name
- [ ] Test one thing (single responsibility)
- [ ] Be independent (no test dependencies)
- [ ] Be deterministic (same result every time)
- [ ] Be fast (< 1s for unit tests)
- [ ] Have clear Given/When/Then structure
- [ ] Clean up after itself (no side effects)
- [ ] Have appropriate assertions
- [ ] Test both success and failure cases

### 11.2 Test Code Quality

- **No duplicated test code** - use fixtures
- **No flaky tests** - fix or remove
- **No skipped tests** - fix or document why
- **Clear failure messages** - easy to debug

---

## 12. Test Maintenance

### 12.1 Refactoring Tests

When refactoring tests:
- Maintain test coverage
- Keep tests passing
- Update test documentation
- Review test quality

### 12.2 Adding New Tests

When adding new agent types:
- Follow existing test patterns
- Add to all 3 test levels (unit, integration, e2e)
- Update coverage requirements
- Update this document

---

## 13. Performance Testing

### 13.1 Performance Benchmarks

**Agent Initialization:**
- Target: < 100ms
- Test: Measure time to create agent instance

**Registry Lookup:**
- Target: < 1ms
- Test: Measure time to get agent type

**Concurrent Execution:**
- Target: 10 agents run concurrently without blocking
- Test: Spawn 10 agents, measure completion time

### 13.2 Load Testing

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_agent_execution_scales():
    """Concurrent execution scales linearly"""
    # Run 1, 5, 10, 20 agents
    # Measure total time
    # Verify linear scaling
```

---

## 14. Test Reporting

### 14.1 Test Results

Generate reports:
```bash
# JUnit XML (for CI)
pytest tests/ --junitxml=test-results.xml

# HTML report
pytest tests/ --html=test-report.html

# Coverage report
pytest tests/ --cov --cov-report=html
```

### 14.2 Test Metrics

Track:
- **Total tests:** ~100+ tests
- **Pass rate:** 100%
- **Coverage:** >90%
- **Execution time:** < 2 minutes (unit + integration)
- **Flakiness:** 0%

---

## 15. Testing Timeline

### 15.1 Test-First Approach

**Week 1:**
- Write unit tests for agent types registry
- Write unit tests for first 4 coding agents
- Implement to pass tests

**Week 2:**
- Write unit tests for next 6 agents (writing, visual, QA, research)
- Implement to pass tests
- Write integration tests

**Week 3:**
- Write unit tests for final 6 agents (security, project)
- Implement to pass tests
- Write E2E tests

**Week 4:**
- Full test suite execution
- Coverage verification
- Performance testing
- Documentation

---

## 16. Test Success Criteria

Phase testing is complete when:
- [ ] All unit tests pass (100%)
- [ ] All integration tests pass (100%)
- [ ] All E2E tests pass (100%)
- [ ] Code coverage ≥ 90%
- [ ] No flaky tests
- [ ] No skipped tests (or documented exceptions)
- [ ] All existing tests still pass (0 regressions)
- [ ] Test execution time < 5 minutes
- [ ] All test quality criteria met

---

## 17. Test Maintenance Plan

### 17.1 Regular Reviews

- Weekly: Review test failures
- Monthly: Review test coverage
- Quarterly: Refactor/clean tests

### 17.2 Test Debt

Track and address:
- Skipped tests
- Flaky tests
- Slow tests
- Missing edge cases
- Low coverage areas
