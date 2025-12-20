# Agent Workflow System: Implementation Plan

**Phase:** agent-workflows
**Version Target:** 1.7.0
**Created:** 2025-12-21
**Status:** Planning

---

## Overview

Enable chaining multiple specialized agents together into coordinated workflows for complex, multi-step development tasks. This builds on the 20 specialized agent types introduced in v1.6.0.

**Current Limitation:**
Users can invoke agents one at a time, but complex tasks (like "Full PR Review" or "Feature Implementation") require manually coordinating multiple agents sequentially or in parallel.

**Goal:**
Create a workflow orchestration system that:
- Chains multiple agents together with explicit dependencies
- Executes agents conditionally based on previous results
- Runs independent agents in parallel for efficiency
- Provides pre-built workflow templates for common tasks
- Tracks progress and supports resumability
- Integrates seamlessly with existing agent system

---

## Current State

### Existing Infrastructure

**Agent System (v1.6.0):**
- 20 specialized agent types across 6 categories
- `AgentTypeRegistry` - Singleton registry of agent type definitions
- `AgentManager` - Manages agent lifecycle and execution
- `Agent` base class - Template method pattern for execution
- `AgentResult` - Structured results with success/failure state
- `AgentConfig` - Factory pattern for agent configuration
- `AgentExecutor` - Handles agent spawning and monitoring

**Session System:**
- `SessionManager` - Conversation persistence
- `SessionStorage` - JSON-based storage
- Message history and context tracking

**Tools & Permissions:**
- Tool execution framework
- Permission checking system
- Hook integration for lifecycle events

**What We Have:**
- Ability to spawn single agents
- Agent-specific tool restrictions
- Resource limit enforcement
- Result collection

**What We Need:**
- Multi-agent coordination
- Workflow definition format
- Execution orchestration
- Progress tracking
- Conditional execution logic
- Parallel execution support
- Template system

---

## Use Cases

### 1. Full PR Review Workflow
```
1. Plan Agent → Analyzes PR scope and creates review plan
2. Code Review Agent → Reviews code quality and patterns
3. Security Audit Agent → Scans for vulnerabilities
4. Test Generation Agent → Creates missing tests
5. Documentation Agent → Updates docs if needed
```

### 2. Bug Fix Workflow
```
1. Debug Agent → Analyzes error and identifies root cause
2. Refactoring Agent (conditional) → If architectural issue, refactor
3. Test Generation Agent → Creates regression tests
4. Code Review Agent → Reviews the fix
```

### 3. Feature Implementation Workflow
```
1. Plan Agent → Creates implementation plan
2. Test Generation Agent → Writes tests (TDD)
3. General Agent → Implements feature
4. Code Review Agent → Reviews implementation
5. Documentation Agent → Updates documentation
```

### 4. Parallel Analysis Workflow
```
Parallel:
  - Log Analysis Agent → Analyzes logs
  - Performance Analysis Agent → Profiles code
  - Dependency Analysis Agent → Checks dependencies
Then:
  - Research Agent → Synthesizes findings into report
```

### 5. Migration Workflow
```
1. Migration Planning Agent → Plans migration strategy
2. Refactoring Agent → Executes code changes
3. Test Generation Agent → Updates tests
4. Security Audit Agent → Verifies security
5. Documentation Agent → Updates migration docs
```

---

## Design Decisions

### 1. Workflow Definition Format

**Decision: YAML-based with optional Python API**

**Rationale:**
- YAML is human-readable and easy to edit
- Python API provides programmatic control
- Matches existing patterns (skills, hooks use YAML)
- Easy to version control
- Clear syntax for dependencies and conditions

**YAML Structure:**
```yaml
name: full-pr-review
description: Comprehensive pull request review workflow
version: 1.0.0

steps:
  - id: plan
    agent: plan
    description: Analyze PR scope
    inputs:
      task: "Review the changes in this PR"

  - id: review
    agent: code-review
    description: Review code quality
    depends_on: [plan]
    inputs:
      focus: "security, performance, maintainability"

  - id: security
    agent: security-audit
    description: Security scan
    depends_on: [plan]
    parallel_with: [review]

  - id: tests
    agent: test-generation
    description: Generate missing tests
    depends_on: [review, security]
    condition: "review.result.coverage < 90"

  - id: docs
    agent: documentation
    description: Update documentation
    depends_on: [review]
    condition: "review.result.docs_needed == true"
```

**Python API:**
```python
from code_forge.workflows import Workflow, Step

workflow = Workflow("full-pr-review")
plan = workflow.add_step("plan", agent="plan")
review = workflow.add_step("review", agent="code-review", depends_on=[plan])
security = workflow.add_step("security", agent="security-audit",
                            depends_on=[plan], parallel_with=[review])
```

### 2. Execution Model

**Decision: Directed Acyclic Graph (DAG) with async execution**

**Rationale:**
- DAG naturally represents dependencies
- Prevents circular dependencies
- Enables topological sort for execution order
- Supports parallel execution of independent steps
- Well-understood pattern (Airflow, Prefect, etc.)

**Architecture:**
```
WorkflowEngine
  ├── Parse YAML/Python → WorkflowDefinition
  ├── Build DAG → WorkflowGraph
  ├── Validate (detect cycles, check agents exist)
  ├── Execute with WorkflowExecutor
  │   ├── Topological sort for order
  │   ├── Parallel execution of independent steps
  │   ├── Conditional step evaluation
  │   └── Progress tracking
  └── Collect results → WorkflowResult
```

### 3. Step Dependencies

**Decision: Explicit dependency declaration with parallel hints**

**Dependency Types:**
1. **depends_on:** Sequential - wait for these steps to complete
2. **parallel_with:** Hint that steps can run concurrently
3. **condition:** Boolean expression evaluated at runtime

**Example:**
```yaml
steps:
  - id: A
    agent: plan

  - id: B
    agent: code-review
    depends_on: [A]

  - id: C
    agent: security-audit
    depends_on: [A]
    parallel_with: [B]  # B and C can run simultaneously

  - id: D
    agent: test-generation
    depends_on: [B, C]  # Wait for both B and C
```

### 4. Conditional Execution

**Decision: Simple expression language for conditions**

**Supported Conditions:**
- Step success: `step_id.success`
- Step failure: `step_id.failed`
- Result values: `step_id.result.field_name`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean logic: `and`, `or`, `not`

**Examples:**
```yaml
condition: "review.success"
condition: "review.result.issues_found > 0"
condition: "plan.result.complexity == 'high' and security.success"
```

### 5. Progress Tracking & Resumability

**Decision: Checkpoint-based resumability with event streaming**

**Features:**
- Each step completion creates checkpoint
- Workflow state persisted to session storage
- Failed workflows can resume from last checkpoint
- Real-time progress events streamed to UI
- Full workflow history maintained

**State Tracking:**
```python
class WorkflowState:
    workflow_id: str
    status: WorkflowStatus  # pending, running, completed, failed, paused
    current_step: str | None
    completed_steps: list[str]
    failed_steps: list[str]
    step_results: dict[str, AgentResult]
    start_time: datetime
    end_time: datetime | None
```

### 6. Workflow Templates

**Decision: Built-in templates + user-defined custom workflows**

**Built-in Templates:**
1. `pr-review` - Full PR review
2. `bug-fix` - Debug and fix workflow
3. `feature-impl` - Feature implementation
4. `security-audit-full` - Comprehensive security audit
5. `code-quality` - Code quality improvement
6. `migration` - Code migration
7. `parallel-analysis` - Multi-agent analysis

**Template Storage:**
- Built-in: `src/code_forge/workflows/templates/`
- User: `~/.forge/workflows/`
- Project: `.forge/workflows/`

**Template Discovery:**
- Auto-scan all locations
- Registry pattern (WorkflowTemplateRegistry)
- List via `/workflow list` command

### 7. Integration Points

**Session Integration:**
- Workflows tied to session
- Workflow messages in session history
- Resume workflows from previous sessions

**Permission System:**
- Workflow execution requires permission
- Individual steps inherit agent permissions
- Hook integration for workflow lifecycle events

**Error Handling:**
- Step failures propagate to workflow
- Configurable failure modes (fail-fast vs. continue)
- Retry logic for transient failures
- Clear error reporting

---

## Architecture

### Component Overview

```
src/code_forge/workflows/
├── __init__.py              # Package exports
├── models.py                # Core data models
│   ├── WorkflowDefinition   # Workflow metadata and steps
│   ├── WorkflowStep         # Single step definition
│   ├── WorkflowState        # Runtime state
│   ├── WorkflowResult       # Final result
│   └── StepResult           # Individual step result
├── parser.py                # YAML/Python parsing
│   ├── YAMLWorkflowParser   # Parse YAML workflows
│   └── PythonWorkflowBuilder # Python API builder
├── graph.py                 # DAG construction and validation
│   ├── WorkflowGraph        # DAG representation
│   ├── GraphValidator       # Cycle detection, validation
│   └── TopologicalSorter    # Execution order calculation
├── conditions.py            # Conditional execution
│   ├── ConditionEvaluator   # Evaluate condition expressions
│   └── ExpressionParser     # Parse condition syntax
├── executor.py              # Workflow execution
│   ├── WorkflowExecutor     # Main execution engine
│   ├── StepExecutor         # Single step execution
│   └── ParallelExecutor     # Parallel step coordination
├── state.py                 # State management
│   ├── StateManager         # State persistence
│   └── CheckpointManager    # Checkpoint creation/restoration
├── templates/               # Built-in workflow templates
│   ├── pr_review.yaml
│   ├── bug_fix.yaml
│   ├── feature_impl.yaml
│   ├── security_audit.yaml
│   ├── code_quality.yaml
│   ├── migration.yaml
│   └── parallel_analysis.yaml
├── registry.py              # Workflow template registry
│   └── WorkflowTemplateRegistry
├── commands.py              # Slash commands
│   └── WorkflowCommand      # /workflow command
└── tool.py                  # Workflow execution tool
    └── WorkflowTool         # LLM-accessible tool
```

### Data Models

```python
@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    description: str
    version: str
    author: str | None
    steps: list[WorkflowStep]
    metadata: dict[str, Any]

@dataclass
class WorkflowStep:
    """Single step in workflow."""
    id: str
    agent: str
    description: str
    inputs: dict[str, Any]
    depends_on: list[str]
    parallel_with: list[str]
    condition: str | None
    timeout: int | None
    max_retries: int

@dataclass
class WorkflowState:
    """Runtime workflow state."""
    workflow_id: str
    definition: WorkflowDefinition
    status: WorkflowStatus
    current_step: str | None
    completed_steps: list[str]
    failed_steps: list[str]
    skipped_steps: list[str]
    step_results: dict[str, StepResult]
    start_time: datetime
    end_time: datetime | None

@dataclass
class StepResult:
    """Result of a single step."""
    step_id: str
    agent_type: str
    agent_result: AgentResult
    start_time: datetime
    end_time: datetime
    duration: float
    success: bool
    error: str | None

@dataclass
class WorkflowResult:
    """Final workflow result."""
    workflow_id: str
    workflow_name: str
    success: bool
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    step_results: dict[str, StepResult]
    duration: float
    error: str | None
```

### Execution Flow

```
1. Parse Workflow Definition (YAML/Python)
   ↓
2. Build Workflow Graph (DAG)
   ↓
3. Validate Graph (cycles, agent existence)
   ↓
4. Create Workflow State
   ↓
5. Calculate Execution Order (topological sort)
   ↓
6. For each step in order:
   a. Evaluate condition (skip if false)
   b. Wait for dependencies
   c. Execute agent
   d. Collect result
   e. Create checkpoint
   f. Update state
   g. Fire events
   ↓
7. Collect Workflow Result
   ↓
8. Persist to session
```

---

## Implementation Steps

### Phase 1: Core Models & Graph (Foundation)

**Files:**
- `workflows/models.py` - All data models
- `workflows/graph.py` - DAG construction and validation

**Tasks:**
1. Define all dataclasses (WorkflowDefinition, WorkflowStep, etc.)
2. Implement WorkflowGraph with adjacency list
3. Implement cycle detection (DFS-based)
4. Implement topological sort
5. Add comprehensive validation

**Tests:**
- Unit tests for all models
- Graph construction tests
- Cycle detection tests
- Topological sort tests
- Validation tests

**Duration:** ~2-3 days

---

### Phase 2: Parsing (YAML & Python API)

**Files:**
- `workflows/parser.py` - YAML and Python parsing

**Tasks:**
1. Implement YAMLWorkflowParser with schema validation
2. Implement PythonWorkflowBuilder fluent API
3. Add comprehensive error handling
4. Support workflow variables/parameters
5. Add validation at parse time

**Tests:**
- YAML parsing tests (valid and invalid)
- Python API tests
- Schema validation tests
- Error handling tests

**Duration:** ~2 days

---

### Phase 3: Conditional Execution

**Files:**
- `workflows/conditions.py` - Condition evaluation

**Tasks:**
1. Implement expression parser (simple recursive descent)
2. Implement ConditionEvaluator
3. Support all comparison operators
4. Support boolean logic (and, or, not)
5. Add result field access (`step.result.field`)

**Tests:**
- Expression parsing tests
- Condition evaluation tests
- Edge cases (missing fields, type errors)

**Duration:** ~2 days

---

### Phase 4: State Management & Checkpointing

**Files:**
- `workflows/state.py` - State persistence

**Tasks:**
1. Implement StateManager with JSON persistence
2. Implement CheckpointManager
3. Add workflow state serialization
4. Support resume from checkpoint
5. Integrate with SessionStorage

**Tests:**
- State persistence tests
- Checkpoint creation/restoration tests
- Serialization tests

**Duration:** ~2 days

---

### Phase 5: Execution Engine

**Files:**
- `workflows/executor.py` - Main execution logic

**Tasks:**
1. Implement WorkflowExecutor main loop
2. Implement StepExecutor for single steps
3. Implement ParallelExecutor using asyncio.gather
4. Add dependency waiting logic
5. Add error handling and retry logic
6. Add progress tracking and events
7. Integrate with AgentManager

**Tests:**
- Sequential execution tests
- Parallel execution tests
- Dependency resolution tests
- Conditional execution tests
- Error handling tests
- Retry logic tests

**Duration:** ~4-5 days

---

### Phase 6: Templates & Registry

**Files:**
- `workflows/templates/*.yaml` - Built-in templates
- `workflows/registry.py` - Template registry

**Tasks:**
1. Create 7 built-in workflow templates
2. Implement WorkflowTemplateRegistry
3. Add template discovery (builtin + user + project)
4. Add template instantiation
5. Support template parameters

**Tests:**
- Template loading tests
- Registry tests
- Discovery tests
- Parameter substitution tests

**Duration:** ~2 days

---

### Phase 7: Commands & Tools

**Files:**
- `workflows/commands.py` - Slash commands
- `workflows/tool.py` - LLM tool

**Tasks:**
1. Implement /workflow command:
   - `/workflow list` - List available templates
   - `/workflow run <name>` - Run workflow
   - `/workflow status <id>` - Check status
   - `/workflow resume <id>` - Resume failed workflow
   - `/workflow cancel <id>` - Cancel running workflow
2. Implement WorkflowTool for LLM access
3. Add permission checks
4. Add hook integration

**Tests:**
- Command execution tests
- Tool tests
- Permission tests
- Hook integration tests

**Duration:** ~2-3 days

---

### Phase 8: Integration & Documentation

**Tasks:**
1. Integration tests (end-to-end workflows)
2. Update CHANGELOG
3. Write user documentation
4. Create workflow examples
5. Update README (if appropriate)

**Duration:** ~2 days

---

## Design Patterns

### Patterns Used

| Pattern | Application |
|---------|-------------|
| **Command** | WorkflowStep encapsulates agent execution |
| **Template Method** | Executor defines execution algorithm |
| **Factory** | WorkflowParser creates workflows from different sources |
| **Strategy** | Different execution strategies (sequential, parallel) |
| **Observer** | Event-based progress tracking |
| **Singleton** | WorkflowTemplateRegistry |
| **Composite** | Workflow is composition of steps |
| **State** | WorkflowState tracks execution state |

### SOLID Principles

- **Single Responsibility:** Each component has one clear purpose
- **Open/Closed:** Easy to add new workflow templates without modifying executor
- **Liskov Substitution:** All workflows execute through same interface
- **Interface Segregation:** Separate interfaces for parsing, execution, state
- **Dependency Inversion:** Executor depends on Agent abstraction

---

## Risks & Mitigations

### Risk 1: Complexity Management
**Problem:** Workflow system is complex with many moving parts
**Mitigation:**
- Phased implementation (8 phases)
- Comprehensive testing at each phase
- Clear separation of concerns
- Extensive documentation

### Risk 2: Deadlocks in Parallel Execution
**Problem:** Parallel steps might deadlock or cause race conditions
**Mitigation:**
- Use asyncio.gather for parallel execution
- No shared mutable state between steps
- Each step gets isolated context
- Comprehensive concurrency tests

### Risk 3: Circular Dependencies
**Problem:** Users might create workflows with circular dependencies
**Mitigation:**
- Graph validation before execution
- Clear error messages
- Prevent workflow from starting if invalid
- Examples showing correct patterns

### Risk 4: Resource Exhaustion
**Problem:** Large workflows might exhaust resources
**Mitigation:**
- Enforce max steps per workflow (e.g., 20)
- Inherit agent resource limits
- Monitor total resource usage
- Add workflow-level timeouts

### Risk 5: State Inconsistency
**Problem:** Checkpoint/resume might have edge cases
**Mitigation:**
- Atomic checkpoint writes
- Validation on restore
- Comprehensive state tests
- Clear error messages

### Risk 6: Condition Expression Security
**Problem:** Eval-like condition parsing could be risky
**Mitigation:**
- NO eval() or exec()
- Safe expression parser (whitelist-based)
- Limit expression complexity
- Validate all field accesses

---

## Success Criteria

### Must Have (v1.7.0)

1. **Core Execution:**
   - Execute workflows with sequential steps
   - Execute workflows with parallel steps
   - Evaluate conditional steps
   - Track workflow state
   - Persist to session

2. **Workflow Definition:**
   - Parse YAML workflows
   - Python API for workflow building
   - Validation (cycles, agents, syntax)

3. **Templates:**
   - 7 built-in workflow templates
   - Template discovery and listing
   - Template execution

4. **Commands:**
   - `/workflow list`
   - `/workflow run <name>`
   - `/workflow status <id>`

5. **Testing:**
   - >90% test coverage
   - All integration tests pass
   - No regressions

6. **Documentation:**
   - Complete planning docs
   - Code documentation
   - User guide
   - Examples

### Should Have (v1.7.x)

1. **Advanced Features:**
   - `/workflow resume <id>`
   - `/workflow cancel <id>`
   - Workflow parameters/variables
   - Custom templates

2. **UI Enhancements:**
   - Progress bar
   - Real-time step updates
   - Workflow visualization

### Could Have (Future)

1. **Advanced Orchestration:**
   - Loop constructs
   - Fork/join patterns
   - Dynamic step generation
   - Sub-workflows

2. **Workflow Marketplace:**
   - Share workflows with community
   - Import workflows from URLs
   - Workflow versioning

---

## Performance Considerations

### Execution Performance

**Optimization Strategies:**
- Parallel execution of independent steps
- Lazy evaluation of conditions
- Efficient graph traversal
- Minimal state serialization overhead

**Expected Performance:**
- Workflow startup: < 100ms
- Step transition: < 50ms
- Checkpoint creation: < 200ms
- State restoration: < 300ms

### Scalability

**Limits:**
- Max steps per workflow: 20
- Max parallel steps: 5
- Max workflow depth: 10 levels
- Max condition complexity: 10 operations

**Rationale:**
- Prevent resource exhaustion
- Maintain responsiveness
- Clear error messages
- Configurable in future versions

---

## Testing Strategy

### Unit Tests
- All models (serialization, validation)
- Graph construction and validation
- Topological sort
- Condition evaluation
- State management
- Parser (YAML and Python)

### Integration Tests
- End-to-end workflow execution
- Sequential workflows
- Parallel workflows
- Conditional workflows
- Error handling
- Resume from checkpoint
- Template execution

### System Tests
- All 7 built-in templates
- Concurrent workflow execution
- Large workflow (20 steps)
- Failure recovery
- Permission integration
- Hook integration

---

## Future Enhancements

### v1.8.0+
1. **Workflow Monitoring:**
   - Execution metrics
   - Performance analytics
   - Cost tracking
   - Success rates

2. **Advanced Control Flow:**
   - Loop constructs (for-each, while)
   - Switch/case patterns
   - Exception handling blocks
   - Timeout per step

3. **Workflow Composition:**
   - Sub-workflows
   - Workflow inheritance
   - Mixins/includes
   - Dynamic workflow generation

4. **Collaboration:**
   - Multi-user workflows
   - Approval gates
   - Review steps
   - Notifications

5. **IDE Integration:**
   - Workflow editor UI
   - Visual workflow designer
   - Debugging tools
   - Breakpoints

---

## Migration & Backward Compatibility

**No Breaking Changes:**
- Agent system unchanged
- All existing functionality preserved
- Workflows are purely additive
- Existing commands still work

**New Capabilities:**
- `/workflow` command family
- WorkflowTool for LLM access
- Workflow templates in config dirs

**User Impact:**
- Zero migration needed
- Opt-in feature
- Backward compatible

---

## References

- FEAT-002: Specialized Agents (v1.6.0)
- FEAT-003: Agent Workflow System (UNDONE.md)
- Existing agent system: `src/code_forge/agents/`
- Session system: `src/code_forge/sessions/`
- Design patterns: Gang of Four
- DAG execution: Airflow, Prefect patterns
