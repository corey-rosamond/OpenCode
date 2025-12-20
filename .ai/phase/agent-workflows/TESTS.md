# Agent Workflow System: Test Strategy

**Phase:** agent-workflows
**Version Target:** 1.7.0
**Created:** 2025-12-21

Comprehensive testing strategy for workflow system implementation.

---

## Testing Philosophy

### Test Pyramid

```
        ┌─────────────┐
        │   E2E (10)  │  ← Real workflows, all systems
        ├─────────────┤
        │ Integration │  ← Component interaction
        │    (40)     │
        ├─────────────┤
        │    Unit     │  ← Individual components
        │   (200+)    │
        └─────────────┘
```

### Target Metrics

- **Total Tests:** 250+
- **Coverage:** ≥ 90%
- **Critical Path Coverage:** 100%
- **All tests pass:** Yes
- **No flaky tests:** Yes

### Testing Principles

1. **Test Behavior, Not Implementation** - Focus on what, not how
2. **Independent Tests** - No test interdependencies
3. **Fast Tests** - Unit tests < 100ms, integration < 1s
4. **Clear Names** - `test_what_when_then` format
5. **AAA Pattern** - Arrange, Act, Assert
6. **Mock External Dependencies** - Control what you don't own

---

## Test Structure

```
tests/
├── unit/
│   └── workflows/
│       ├── test_models.py              # Data models
│       ├── test_graph.py               # Graph construction/validation
│       ├── test_parser.py              # YAML/Python parsing
│       ├── test_conditions.py          # Condition evaluation
│       ├── test_state.py               # State management
│       ├── test_executor.py            # Workflow execution
│       ├── test_templates.py           # Template system
│       ├── test_commands.py            # Slash commands
│       └── test_tool.py                # Workflow tool
├── integration/
│   └── workflows/
│       ├── test_sequential_workflows.py    # Sequential execution
│       ├── test_parallel_workflows.py      # Parallel execution
│       ├── test_conditional_workflows.py   # Conditional steps
│       ├── test_resume_workflows.py        # Checkpoint/resume
│       ├── test_builtin_templates.py       # All 7 templates
│       └── test_full_integration.py        # All systems together
└── e2e/
    └── workflows/
        └── test_real_workflows.py          # Real-world scenarios
```

---

## Unit Tests (200+ tests)

### 1. Models (test_models.py)

**Test Coverage:**
- [ ] WorkflowDefinition creation and validation
- [ ] WorkflowStep creation and validation
- [ ] WorkflowState creation and transitions
- [ ] StepResult creation
- [ ] WorkflowResult aggregation
- [ ] JSON serialization/deserialization
- [ ] Equality comparison
- [ ] Invalid data rejection

**Example Tests:**

```python
class TestWorkflowDefinition:
    def test_create_valid_definition(self):
        """Given valid workflow data, creates WorkflowDefinition"""

    def test_reject_missing_name(self):
        """Given workflow without name, raises ValidationError"""

    def test_serialize_to_json(self):
        """Given WorkflowDefinition, serializes to valid JSON"""

    def test_deserialize_from_json(self):
        """Given valid JSON, creates WorkflowDefinition"""

class TestWorkflowState:
    def test_transition_to_running(self):
        """Given pending state, transitions to running"""

    def test_record_completed_step(self):
        """Given completed step, adds to completed_steps list"""

    def test_record_failed_step(self):
        """Given failed step, adds to failed_steps list"""
```

**Expected Count:** ~40 tests

---

### 2. Graph (test_graph.py)

**Test Coverage:**
- [ ] Graph construction from workflow definition
- [ ] Add nodes (steps) to graph
- [ ] Add edges (dependencies) to graph
- [ ] Detect cycles (various configurations)
- [ ] Topological sort for valid DAG
- [ ] Topological sort fails on cyclic graph
- [ ] Identify parallel execution opportunities
- [ ] Validate all referenced agents exist
- [ ] Validate all referenced steps exist
- [ ] Detect orphaned steps (no path to/from)

**Example Tests:**

```python
class TestWorkflowGraph:
    def test_build_simple_graph(self):
        """Given 3 sequential steps, builds valid graph"""

    def test_detect_simple_cycle(self):
        """Given A→B→C→A, detects cycle"""

    def test_detect_self_reference_cycle(self):
        """Given A→A, detects self-reference"""

    def test_topological_sort_linear(self):
        """Given A→B→C, returns [A, B, C]"""

    def test_topological_sort_diamond(self):
        """Given diamond pattern, returns valid order"""

    def test_identify_parallel_steps(self):
        """Given A→(B,C)→D with parallel_with, identifies B,C"""

    def test_reject_nonexistent_agent(self):
        """Given step with invalid agent type, raises error"""
```

**Expected Count:** ~30 tests

---

### 3. Parser (test_parser.py)

**Test Coverage:**
- [ ] Parse valid YAML workflow
- [ ] Parse YAML with all features (deps, conditions, parallel)
- [ ] Reject invalid YAML syntax
- [ ] Reject missing required fields
- [ ] Reject invalid field types
- [ ] Python API fluent interface
- [ ] Python API produces same result as YAML
- [ ] Schema validation
- [ ] Clear error messages
- [ ] Parameter substitution in templates

**Example Tests:**

```python
class TestYAMLParser:
    def test_parse_simple_yaml_workflow(self):
        """Given valid YAML, returns WorkflowDefinition"""

    def test_parse_yaml_with_dependencies(self):
        """Given YAML with depends_on, preserves dependencies"""

    def test_parse_yaml_with_conditions(self):
        """Given YAML with conditions, preserves conditions"""

    def test_reject_invalid_yaml_syntax(self):
        """Given malformed YAML, raises clear error"""

    def test_reject_missing_required_field(self):
        """Given YAML missing 'name', raises ValidationError"""

class TestPythonWorkflowBuilder:
    def test_fluent_api_builds_workflow(self):
        """Given builder operations, produces WorkflowDefinition"""

    def test_python_api_matches_yaml(self):
        """Given same workflow in YAML and Python, results match"""
```

**Expected Count:** ~25 tests

---

### 4. Conditions (test_conditions.py)

**Test Coverage:**
- [ ] Parse simple comparison: `step.success`
- [ ] Parse field access: `step.result.value`
- [ ] Parse operators: ==, !=, <, >, <=, >=
- [ ] Parse boolean logic: and, or, not
- [ ] Parse nested expressions
- [ ] Evaluate true condition
- [ ] Evaluate false condition
- [ ] Handle missing fields gracefully
- [ ] Handle type mismatches
- [ ] Reject unsafe expressions (no eval/exec)

**Example Tests:**

```python
class TestExpressionParser:
    def test_parse_success_check(self):
        """Given 'step.success', parses to AST"""

    def test_parse_field_comparison(self):
        """Given 'step.result.count > 5', parses to AST"""

    def test_parse_boolean_and(self):
        """Given 'A.success and B.success', parses correctly"""

    def test_reject_eval_attempt(self):
        """Given '__import__', rejects as unsafe"""

class TestConditionEvaluator:
    def test_evaluate_true_condition(self):
        """Given true condition and context, returns True"""

    def test_evaluate_false_condition(self):
        """Given false condition and context, returns False"""

    def test_handle_missing_field(self):
        """Given missing field, returns False and logs warning"""

    def test_complex_boolean_logic(self):
        """Given (A and B) or C, evaluates correctly"""
```

**Expected Count:** ~20 tests

---

### 5. State Management (test_state.py)

**Test Coverage:**
- [ ] Save workflow state to storage
- [ ] Load workflow state from storage
- [ ] Delete workflow state
- [ ] List all saved states
- [ ] Create checkpoint after step
- [ ] Restore from checkpoint
- [ ] List checkpoints for workflow
- [ ] Atomic checkpoint writes
- [ ] State serialization correctness
- [ ] State deserialization validation

**Example Tests:**

```python
class TestStateManager:
    def test_save_workflow_state(self):
        """Given WorkflowState, persists to storage"""

    def test_load_workflow_state(self):
        """Given saved state, loads WorkflowState"""

    def test_atomic_state_write(self):
        """Given concurrent writes, maintains consistency"""

class TestCheckpointManager:
    def test_create_checkpoint_after_step(self):
        """Given completed step, creates checkpoint"""

    def test_restore_from_checkpoint(self):
        """Given checkpoint, restores workflow state"""

    def test_list_checkpoints_for_workflow(self):
        """Given workflow ID, lists all checkpoints"""
```

**Expected Count:** ~20 tests

---

### 6. Executor (test_executor.py)

**Test Coverage:**
- [ ] Execute simple 2-step workflow
- [ ] Execute 3+ step sequential workflow
- [ ] Execute parallel steps
- [ ] Execute conditional steps
- [ ] Skip step when condition is false
- [ ] Wait for dependencies before executing
- [ ] Handle agent execution failure
- [ ] Retry failed steps
- [ ] Propagate failures to dependent steps
- [ ] Enforce max parallel limit
- [ ] Enforce workflow timeout
- [ ] Create checkpoints during execution
- [ ] Fire lifecycle events
- [ ] Collect final WorkflowResult

**Example Tests:**

```python
class TestWorkflowExecutor:
    async def test_execute_sequential_workflow(self):
        """Given A→B→C workflow, executes in order"""

    async def test_execute_parallel_workflow(self):
        """Given parallel steps, executes concurrently"""

    async def test_skip_conditional_step(self):
        """Given false condition, skips step"""

    async def test_handle_step_failure(self):
        """Given failed step, records failure and skips dependents"""

    async def test_enforce_max_parallel(self):
        """Given 8 parallel steps, limits to max_parallel"""

    async def test_create_checkpoints(self):
        """Given executing workflow, creates checkpoint after each step"""

class TestStepExecutor:
    async def test_execute_single_step(self):
        """Given step config, spawns agent and collects result"""

    async def test_evaluate_condition_before_execution(self):
        """Given conditional step, evaluates condition first"""

    async def test_wait_for_dependencies(self):
        """Given step with dependencies, waits for completion"""
```

**Expected Count:** ~40 tests

---

### 7. Templates (test_templates.py)

**Test Coverage:**
- [ ] Load template from YAML file
- [ ] Validate template structure
- [ ] Register template in registry
- [ ] Retrieve template by name
- [ ] List all registered templates
- [ ] Discover built-in templates
- [ ] Discover user templates
- [ ] Discover project templates
- [ ] Instantiate template with parameters
- [ ] Parameter substitution
- [ ] Reject invalid templates

**Example Tests:**

```python
class TestTemplateRegistry:
    def test_register_template(self):
        """Given valid template, registers in registry"""

    def test_retrieve_template_by_name(self):
        """Given registered template, retrieves by name"""

    def test_list_all_templates(self):
        """Given multiple templates, lists all"""

    def test_discover_builtin_templates(self):
        """Given builtin templates directory, discovers all 7"""

    def test_discover_user_templates(self):
        """Given user templates in ~/.forge, discovers them"""

class TestTemplateInstantiation:
    def test_instantiate_with_parameters(self):
        """Given template with params, substitutes values"""
```

**Expected Count:** ~15 tests

---

### 8. Commands (test_commands.py)

**Test Coverage:**
- [ ] `/workflow list` command execution
- [ ] `/workflow run <name>` command execution
- [ ] `/workflow status <id>` command execution
- [ ] `/workflow resume <id>` command execution
- [ ] `/workflow cancel <id>` command execution
- [ ] Command argument parsing
- [ ] Command error handling
- [ ] Command help text
- [ ] Command permissions
- [ ] Invalid command arguments

**Example Tests:**

```python
class TestWorkflowCommand:
    async def test_list_command(self):
        """Given /workflow list, returns template list"""

    async def test_run_command(self):
        """Given /workflow run pr_review, executes workflow"""

    async def test_status_command(self):
        """Given /workflow status <id>, returns status"""

    async def test_invalid_workflow_name(self):
        """Given /workflow run invalid, returns error"""

    async def test_missing_arguments(self):
        """Given /workflow run without name, returns error"""
```

**Expected Count:** ~15 tests

---

### 9. Tool (test_tool.py)

**Test Coverage:**
- [ ] WorkflowTool registration
- [ ] Tool name and description
- [ ] Tool parameters
- [ ] Execute workflow via tool
- [ ] Return structured ToolResult
- [ ] Handle workflow failures
- [ ] Permission integration
- [ ] Tool accessible to LLM

**Example Tests:**

```python
class TestWorkflowTool:
    def test_tool_registration(self):
        """Given WorkflowTool, registers in ToolRegistry"""

    async def test_execute_workflow_via_tool(self):
        """Given tool call, executes workflow"""

    async def test_return_structured_result(self):
        """Given completed workflow, returns ToolResult"""

    async def test_handle_workflow_failure(self):
        """Given failed workflow, returns error in ToolResult"""
```

**Expected Count:** ~10 tests

---

## Integration Tests (40 tests)

### 10. Sequential Workflows (test_sequential_workflows.py)

**Test Coverage:**
- [ ] Simple 2-step workflow end-to-end
- [ ] Complex 5-step workflow
- [ ] Workflow with all step types
- [ ] Failure propagation through chain
- [ ] Results collected correctly

**Example Tests:**

```python
class TestSequentialWorkflows:
    async def test_simple_two_step_workflow(self):
        """Given 2-step workflow, executes end-to-end successfully"""

    async def test_five_step_workflow(self):
        """Given 5-step workflow, all steps execute in order"""

    async def test_failure_stops_execution(self):
        """Given failure in step 2, step 3+ don't execute"""
```

**Expected Count:** ~8 tests

---

### 11. Parallel Workflows (test_parallel_workflows.py)

**Test Coverage:**
- [ ] 2 parallel steps execution
- [ ] 5+ parallel steps with limit
- [ ] Mixed sequential and parallel
- [ ] Diamond pattern execution
- [ ] Partial failure in parallel steps

**Example Tests:**

```python
class TestParallelWorkflows:
    async def test_two_parallel_steps(self):
        """Given 2 parallel steps, both execute concurrently"""

    async def test_respect_max_parallel_limit(self):
        """Given 8 parallel steps, only 5 run concurrently"""

    async def test_diamond_pattern(self):
        """Given A→(B,C)→D, executes correctly"""
```

**Expected Count:** ~8 tests

---

### 12. Conditional Workflows (test_conditional_workflows.py)

**Test Coverage:**
- [ ] Step executes when condition true
- [ ] Step skips when condition false
- [ ] Complex conditional logic
- [ ] Condition evaluation errors handled
- [ ] Conditional with parallel execution

**Example Tests:**

```python
class TestConditionalWorkflows:
    async def test_execute_when_true(self):
        """Given true condition, step executes"""

    async def test_skip_when_false(self):
        """Given false condition, step skips"""

    async def test_complex_condition(self):
        """Given (A and B) or C condition, evaluates correctly"""
```

**Expected Count:** ~6 tests

---

### 13. Resume Workflows (test_resume_workflows.py)

**Test Coverage:**
- [ ] Resume after single step failure
- [ ] Resume after multiple completions
- [ ] Resume from specific checkpoint
- [ ] Skip completed steps on resume
- [ ] Re-execute failed step on resume

**Example Tests:**

```python
class TestResumeWorkflows:
    async def test_resume_after_failure(self):
        """Given failed workflow, resumes from failure point"""

    async def test_skip_completed_steps(self):
        """Given resume, skips already completed steps"""

    async def test_resume_from_checkpoint(self):
        """Given checkpoint ID, resumes from that point"""
```

**Expected Count:** ~6 tests

---

### 14. Built-in Templates (test_builtin_templates.py)

**Test Coverage:**
- [ ] pr_review template executes successfully
- [ ] bug_fix template executes successfully
- [ ] feature_impl template executes successfully
- [ ] security_audit template executes successfully
- [ ] code_quality template executes successfully
- [ ] migration template executes successfully
- [ ] parallel_analysis template executes successfully

**Example Tests:**

```python
class TestBuiltinTemplates:
    async def test_pr_review_template(self):
        """Given pr_review template, executes all steps successfully"""

    async def test_bug_fix_template(self):
        """Given bug_fix template, executes debug→fix→test→review"""

    # ... one test per template
```

**Expected Count:** ~7 tests

---

### 15. Full Integration (test_full_integration.py)

**Test Coverage:**
- [ ] Workflow with all systems (agents, sessions, permissions, hooks)
- [ ] Multiple workflows in same session
- [ ] Concurrent workflow execution
- [ ] Permission checks during execution
- [ ] Hooks fire correctly
- [ ] Session persistence works

**Example Tests:**

```python
class TestFullIntegration:
    async def test_full_workflow_with_all_systems(self):
        """Given workflow, integrates with all systems successfully"""

    async def test_concurrent_workflows(self):
        """Given 3 concurrent workflows, all execute correctly"""

    async def test_permission_integration(self):
        """Given workflow requiring permission, prompts user"""

    async def test_hook_integration(self):
        """Given lifecycle hooks, fires at correct times"""
```

**Expected Count:** ~5 tests

---

## End-to-End Tests (10 tests)

### 16. Real Workflows (test_real_workflows.py)

**Test Coverage:**
- [ ] Real PR review on actual PR
- [ ] Real bug fix workflow on actual bug
- [ ] Real feature implementation workflow
- [ ] User-defined custom workflow
- [ ] Workflow with errors and recovery
- [ ] Large workflow (20 steps)
- [ ] Workflow via LLM tool call
- [ ] Workflow via slash command

**Example Tests:**

```python
class TestRealWorkflows:
    @pytest.mark.slow
    async def test_real_pr_review(self):
        """Given actual PR, runs full review workflow"""

    @pytest.mark.slow
    async def test_real_bug_fix(self):
        """Given real bug report, executes fix workflow"""

    @pytest.mark.slow
    async def test_large_workflow(self):
        """Given 20-step workflow, completes successfully"""
```

**Expected Count:** ~10 tests

---

## Test Infrastructure

### Fixtures (conftest.py)

```python
@pytest.fixture
def workflow_definition():
    """Returns a simple WorkflowDefinition for testing"""

@pytest.fixture
def mock_agent_manager():
    """Returns a mocked AgentManager"""

@pytest.fixture
def mock_session_storage():
    """Returns a mocked SessionStorage"""

@pytest.fixture
def workflow_executor(mock_agent_manager):
    """Returns WorkflowExecutor with mocked dependencies"""

@pytest.fixture
def temp_workflow_dir(tmp_path):
    """Returns temporary directory for workflow files"""
```

### Mock Agents

```python
class MockAgent:
    """Mock agent for testing"""

    async def execute(self):
        return AgentResult.ok("Mock result")

class FailingMockAgent:
    """Mock agent that always fails"""

    async def execute(self):
        return AgentResult.fail("Mock error")
```

### Test Utilities

```python
def create_test_workflow(steps: int, parallel: bool = False):
    """Creates a test workflow with N steps"""

def create_test_graph(pattern: str):
    """Creates test graph from pattern (e.g., 'A->B->C')"""

async def execute_and_wait(workflow):
    """Executes workflow and waits for completion"""
```

---

## Test Execution

### Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/workflows/

# Integration tests only
pytest tests/integration/workflows/

# E2E tests only
pytest tests/e2e/workflows/

# Specific test file
pytest tests/unit/workflows/test_graph.py

# Specific test
pytest tests/unit/workflows/test_graph.py::test_detect_cycle

# With coverage
pytest tests/ --cov=src/code_forge/workflows --cov-report=html

# Verbose
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Run in parallel
pytest tests/ -n auto
```

### Performance Benchmarks

```bash
# Fast unit tests
pytest tests/unit/workflows/ --durations=10

# Identify slow tests
pytest tests/ --durations=20
```

### Coverage Requirements

```bash
# Must pass 90% coverage
pytest tests/ --cov=src/code_forge/workflows --cov-fail-under=90
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Workflow Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/workflows/ -v
      - name: Run integration tests
        run: pytest tests/integration/workflows/ -v
      - name: Check coverage
        run: pytest tests/ --cov=src/code_forge/workflows --cov-fail-under=90
```

---

## Test Maintenance

### Test Quality Checklist

- [ ] All tests are independent
- [ ] No flaky tests
- [ ] Clear test names
- [ ] AAA pattern followed
- [ ] Appropriate assertions
- [ ] Proper cleanup
- [ ] Fast execution (< targets)
- [ ] Good coverage

### Red Flags

- Tests that sleep/wait
- Tests with random behavior
- Tests that depend on external services
- Tests that fail intermittently
- Tests with unclear names
- Tests testing implementation not behavior

---

## Summary

**Total Test Count:** ~250 tests
- Unit Tests: ~200
- Integration Tests: ~40
- E2E Tests: ~10

**Coverage Target:** ≥ 90%

**Critical Paths:** 100% coverage
- Sequential execution
- Parallel execution
- Conditional execution
- State persistence
- Error handling

**Test Execution Time:**
- Unit tests: < 20 seconds
- Integration tests: < 60 seconds
- E2E tests: < 120 seconds
- Total: < 3 minutes

**Quality Gates:**
- All tests pass
- Coverage ≥ 90%
- No flaky tests
- No skipped tests (or justified)
- Type checking passes
- Linting passes

When all tests pass and coverage meets target, the workflow system is ready for production.
