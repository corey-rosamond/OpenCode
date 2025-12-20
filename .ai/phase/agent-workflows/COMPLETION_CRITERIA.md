# Agent Workflow System: Completion Criteria

**Phase:** agent-workflows
**Version Target:** 1.7.0
**Created:** 2025-12-21

All criteria must be met before marking this phase complete.

---

## 1. Core Data Models

### 1.1 File Existence
- [ ] `src/code_forge/workflows/__init__.py` exists
- [ ] `src/code_forge/workflows/models.py` exists
- [ ] Module has comprehensive docstring

### 1.2 Model Definitions
- [ ] `WorkflowDefinition` dataclass defined with all fields
- [ ] `WorkflowStep` dataclass defined with all fields
- [ ] `WorkflowState` dataclass defined with all fields
- [ ] `StepResult` dataclass defined with all fields
- [ ] `WorkflowResult` dataclass defined with all fields
- [ ] `WorkflowStatus` enum defined (pending, running, completed, failed, paused)

### 1.3 Model Functionality
- [ ] All models have type hints
- [ ] All models have docstrings
- [ ] Models are serializable to JSON
- [ ] Models can be deserialized from JSON
- [ ] Validation methods exist where appropriate
- [ ] Equality comparison works correctly

---

## 2. Graph Construction & Validation

### 2.1 File Existence
- [ ] `src/code_forge/workflows/graph.py` exists
- [ ] Module has comprehensive docstring

### 2.2 WorkflowGraph Implementation
- [ ] `WorkflowGraph` class implemented
- [ ] Adjacency list representation
- [ ] `add_step()` method adds nodes
- [ ] `add_dependency()` method adds edges
- [ ] `get_dependencies()` returns dependencies for a step
- [ ] `get_parallel_steps()` identifies parallel execution opportunities
- [ ] Graph is immutable after construction

### 2.3 Validation
- [ ] `GraphValidator` class implemented
- [ ] Cycle detection using DFS
- [ ] `validate()` method checks for cycles
- [ ] `validate()` checks all referenced agents exist
- [ ] `validate()` checks all dependency step IDs exist
- [ ] `validate()` checks for orphaned steps
- [ ] Clear error messages for each validation failure

### 2.4 Topological Sort
- [ ] `TopologicalSorter` class implemented
- [ ] Kahn's or DFS-based algorithm
- [ ] Returns valid execution order
- [ ] Handles parallel execution hints
- [ ] Raises error on cyclic graph

---

## 3. Workflow Parsing

### 3.1 File Existence
- [ ] `src/code_forge/workflows/parser.py` exists
- [ ] Module has comprehensive docstring

### 3.2 YAML Parser
- [ ] `YAMLWorkflowParser` class implemented
- [ ] `parse()` method accepts YAML string or Path
- [ ] Schema validation using Pydantic or similar
- [ ] Returns `WorkflowDefinition`
- [ ] Validates required fields (name, steps)
- [ ] Validates step structure
- [ ] Clear error messages for invalid YAML
- [ ] Supports all workflow features (dependencies, conditions, parallel)

### 3.3 Python API
- [ ] `PythonWorkflowBuilder` class implemented
- [ ] Fluent API design
- [ ] `add_step()` method
- [ ] `set_dependency()` method
- [ ] `set_condition()` method
- [ ] `set_parallel()` method
- [ ] `build()` returns `WorkflowDefinition`
- [ ] Validates during construction

### 3.4 Parser Testing
- [ ] Valid YAML workflows parse correctly
- [ ] Invalid YAML produces clear errors
- [ ] Python API produces same result as YAML
- [ ] Edge cases handled (empty workflows, single step, etc.)

---

## 4. Conditional Execution

### 4.1 File Existence
- [ ] `src/code_forge/workflows/conditions.py` exists
- [ ] Module has comprehensive docstring

### 4.2 Expression Parser
- [ ] `ExpressionParser` class implemented
- [ ] Parses comparison operators: ==, !=, <, >, <=, >=
- [ ] Parses boolean operators: and, or, not
- [ ] Parses field access: `step_id.result.field_name`
- [ ] Parses literals: true, false, numbers, strings
- [ ] Returns abstract syntax tree (AST)
- [ ] NO use of eval() or exec()

### 4.3 Condition Evaluator
- [ ] `ConditionEvaluator` class implemented
- [ ] `evaluate()` method takes expression and context
- [ ] Context contains step results
- [ ] Safely evaluates AST
- [ ] Handles missing fields gracefully
- [ ] Handles type mismatches
- [ ] Returns boolean result
- [ ] Clear error messages

### 4.4 Supported Expressions
- [ ] Simple success check: `step_id.success`
- [ ] Field comparison: `step_id.result.value > 10`
- [ ] Boolean logic: `A.success and B.success`
- [ ] Nested field access: `step.result.data.count`
- [ ] String comparison: `step.result.status == "done"`

---

## 5. State Management & Checkpointing

### 5.1 File Existence
- [ ] `src/code_forge/workflows/state.py` exists
- [ ] Module has comprehensive docstring

### 5.2 StateManager
- [ ] `StateManager` class implemented
- [ ] `save_state()` persists WorkflowState
- [ ] `load_state()` restores WorkflowState
- [ ] `delete_state()` removes saved state
- [ ] `list_states()` returns all saved workflows
- [ ] Integration with SessionStorage
- [ ] Atomic writes (no partial states)

### 5.3 CheckpointManager
- [ ] `CheckpointManager` class implemented
- [ ] `create_checkpoint()` after each step
- [ ] `restore_checkpoint()` restores from checkpoint
- [ ] `list_checkpoints()` for a workflow
- [ ] Checkpoint includes step results
- [ ] Checkpoint includes current state
- [ ] Resume from any checkpoint

### 5.4 State Persistence
- [ ] States saved to JSON files
- [ ] File naming convention: `workflow_{id}.json`
- [ ] Location: `.forge/workflows/states/`
- [ ] Serialization handles all types
- [ ] Deserialization validates structure

---

## 6. Workflow Execution

### 6.1 File Existence
- [ ] `src/code_forge/workflows/executor.py` exists
- [ ] Module has comprehensive docstring

### 6.2 WorkflowExecutor
- [ ] `WorkflowExecutor` class implemented
- [ ] `execute()` method is async
- [ ] Takes `WorkflowDefinition` as input
- [ ] Returns `WorkflowResult`
- [ ] Creates and manages `WorkflowState`
- [ ] Validates workflow before execution
- [ ] Handles execution order via topological sort
- [ ] Creates checkpoints after each step
- [ ] Fires lifecycle events (start, step, complete, fail)

### 6.3 StepExecutor
- [ ] `StepExecutor` class implemented
- [ ] `execute_step()` method is async
- [ ] Evaluates step condition
- [ ] Skips step if condition is false
- [ ] Waits for dependencies to complete
- [ ] Spawns appropriate agent via AgentManager
- [ ] Collects agent result
- [ ] Returns `StepResult`
- [ ] Handles agent failures gracefully
- [ ] Supports retry logic

### 6.4 ParallelExecutor
- [ ] `ParallelExecutor` class implemented
- [ ] Identifies parallelizable steps
- [ ] Uses asyncio.gather for concurrency
- [ ] Limits max parallel steps (default 5)
- [ ] Handles partial failures
- [ ] Maintains result ordering
- [ ] Thread-safe state updates

### 6.5 Error Handling
- [ ] Agent execution errors captured
- [ ] Step failures recorded in state
- [ ] Workflow marked as failed on critical error
- [ ] Continue-on-error mode (configurable)
- [ ] Clear error messages propagated
- [ ] Stack traces logged but not exposed to user

### 6.6 Resource Management
- [ ] Workflow-level timeout enforced
- [ ] Max steps per workflow (default 20)
- [ ] Max parallel steps (default 5)
- [ ] Agent resource limits inherited
- [ ] Cleanup on failure or cancellation

---

## 7. Workflow Templates

### 7.1 Built-in Templates
- [ ] `templates/pr_review.yaml` - Full PR review workflow
- [ ] `templates/bug_fix.yaml` - Bug fix workflow
- [ ] `templates/feature_impl.yaml` - Feature implementation
- [ ] `templates/security_audit.yaml` - Security audit
- [ ] `templates/code_quality.yaml` - Code quality improvement
- [ ] `templates/migration.yaml` - Code migration
- [ ] `templates/parallel_analysis.yaml` - Multi-agent analysis

### 7.2 Template Quality
For EACH template:
- [ ] Valid YAML syntax
- [ ] Complete metadata (name, description, version, author)
- [ ] Clear step descriptions
- [ ] Appropriate agent types used
- [ ] Dependencies correctly specified
- [ ] Conditions are valid (if used)
- [ ] Parallel hints where appropriate
- [ ] Template documentation/comments

### 7.3 Template Registry
- [ ] `WorkflowTemplateRegistry` class implemented (Singleton)
- [ ] `register()` method adds templates
- [ ] `get()` method retrieves by name
- [ ] `list()` method lists all templates
- [ ] `exists()` checks if template exists
- [ ] Auto-discovery from directories:
  - [ ] `src/code_forge/workflows/templates/` (built-in)
  - [ ] `~/.forge/workflows/` (user)
  - [ ] `.forge/workflows/` (project)
- [ ] Thread-safe with RLock
- [ ] Templates validated on registration

### 7.4 Template Instantiation
- [ ] Templates can be instantiated with parameters
- [ ] Parameter substitution in step inputs
- [ ] Validation after instantiation

---

## 8. Commands & Tools

### 8.1 Workflow Command
- [ ] `WorkflowCommand` class implemented
- [ ] Inherits from `Command` base class
- [ ] `/workflow list` - Lists available templates
- [ ] `/workflow run <name>` - Runs a workflow template
- [ ] `/workflow status <id>` - Shows workflow status
- [ ] `/workflow resume <id>` - Resumes failed workflow (optional)
- [ ] `/workflow cancel <id>` - Cancels running workflow (optional)
- [ ] Command registered in CommandRegistry
- [ ] Help text is clear and comprehensive
- [ ] Proper error handling

### 8.2 Workflow Tool
- [ ] `WorkflowTool` class implemented
- [ ] Inherits from `BaseTool`
- [ ] Tool name: "workflow"
- [ ] Tool description for LLM
- [ ] Parameters: workflow_name, inputs
- [ ] Executes workflows via WorkflowExecutor
- [ ] Returns structured results
- [ ] Tool registered in ToolRegistry

### 8.3 Permission Integration
- [ ] Workflow execution requires permission
- [ ] Permission rule: `tool:workflow:*`
- [ ] Default level: ASK
- [ ] Clear permission prompts
- [ ] Individual agent permissions still apply

### 8.4 Hook Integration
- [ ] Workflow lifecycle hooks supported:
  - [ ] `workflow:pre_execute`
  - [ ] `workflow:post_execute`
  - [ ] `workflow:step_complete`
  - [ ] `workflow:failed`
- [ ] Hooks receive workflow metadata
- [ ] Hook failures logged but don't block execution

---

## 9. Session Integration

### 9.1 Workflow in Sessions
- [ ] Workflow execution messages in session history
- [ ] Workflow state persisted to session
- [ ] WorkflowResult stored in session
- [ ] Step results accessible in session
- [ ] Workflow can be resumed from previous session

### 9.2 Session Commands
- [ ] `/session` command shows active workflows
- [ ] Session export includes workflow data
- [ ] Session import restores workflows

---

## 10. Testing

### 10.1 Unit Tests - Models
- [ ] `tests/unit/workflows/test_models.py` exists
- [ ] Test all model creation
- [ ] Test serialization/deserialization
- [ ] Test validation methods
- [ ] Test equality comparison
- [ ] All tests pass

### 10.2 Unit Tests - Graph
- [ ] `tests/unit/workflows/test_graph.py` exists
- [ ] Test graph construction
- [ ] Test cycle detection (with cycles)
- [ ] Test cycle detection (without cycles)
- [ ] Test topological sort
- [ ] Test validation errors
- [ ] All tests pass

### 10.3 Unit Tests - Parser
- [ ] `tests/unit/workflows/test_parser.py` exists
- [ ] Test YAML parsing (valid)
- [ ] Test YAML parsing (invalid)
- [ ] Test Python API
- [ ] Test schema validation
- [ ] Test error messages
- [ ] All tests pass

### 10.4 Unit Tests - Conditions
- [ ] `tests/unit/workflows/test_conditions.py` exists
- [ ] Test expression parsing
- [ ] Test condition evaluation
- [ ] Test all operators
- [ ] Test field access
- [ ] Test error handling
- [ ] All tests pass

### 10.5 Unit Tests - State
- [ ] `tests/unit/workflows/test_state.py` exists
- [ ] Test state persistence
- [ ] Test checkpoint creation
- [ ] Test checkpoint restoration
- [ ] Test state serialization
- [ ] All tests pass

### 10.6 Unit Tests - Executor
- [ ] `tests/unit/workflows/test_executor.py` exists
- [ ] Test sequential execution
- [ ] Test parallel execution
- [ ] Test conditional execution
- [ ] Test dependency resolution
- [ ] Test error handling
- [ ] Test retry logic
- [ ] All tests pass

### 10.7 Unit Tests - Templates
- [ ] `tests/unit/workflows/test_templates.py` exists
- [ ] Test template loading
- [ ] Test template registry
- [ ] Test template discovery
- [ ] Test template validation
- [ ] All tests pass

### 10.8 Unit Tests - Commands
- [ ] `tests/unit/workflows/test_commands.py` exists
- [ ] Test all workflow commands
- [ ] Test command parsing
- [ ] Test error handling
- [ ] All tests pass

### 10.9 Integration Tests
- [ ] `tests/integration/test_workflows.py` exists
- [ ] Test end-to-end workflow execution
- [ ] Test all 7 built-in templates
- [ ] Test sequential workflows
- [ ] Test parallel workflows
- [ ] Test conditional workflows
- [ ] Test workflow resume
- [ ] Test error recovery
- [ ] Test permission integration
- [ ] Test hook integration
- [ ] All tests pass

### 10.10 Test Coverage
- [ ] Overall workflow module coverage ≥ 90%
- [ ] All critical paths tested
- [ ] Edge cases covered
- [ ] Error paths tested

### 10.11 Regression Tests
- [ ] All existing tests still pass
- [ ] No regressions in agent system
- [ ] No regressions in session system
- [ ] No regressions in command system

---

## 11. Code Quality

### 11.1 Type Hints
- [ ] All functions have parameter type hints
- [ ] All functions have return type hints
- [ ] No unnecessary `Any` types
- [ ] Type hints are accurate

### 11.2 Docstrings
- [ ] All modules have docstrings
- [ ] All classes have docstrings (Google style)
- [ ] All public methods have docstrings
- [ ] Parameter descriptions
- [ ] Return value descriptions
- [ ] Exception descriptions

### 11.3 Code Style
- [ ] Follows PEP 8
- [ ] `ruff check src/code_forge/workflows/` passes
- [ ] `mypy src/code_forge/workflows/` passes
- [ ] No unused imports
- [ ] No unused variables
- [ ] Line length ≤ 100 characters

### 11.4 Design Patterns
- [ ] Patterns documented in code
- [ ] Singleton pattern for registry
- [ ] Command pattern for steps
- [ ] Factory pattern for workflow creation
- [ ] Observer pattern for events
- [ ] SOLID principles followed

---

## 12. Documentation

### 12.1 Planning Documents
- [x] PLAN.md - Complete and comprehensive
- [ ] COMPLETION_CRITERIA.md - This document
- [ ] GHERKIN.md - All scenarios defined
- [ ] DEPENDENCIES.md - Dependencies documented
- [ ] TESTS.md - Test strategy defined
- [ ] REVIEW.md - Review checklist created

### 12.2 Code Documentation
- [ ] All new modules documented
- [ ] All new classes documented
- [ ] All new methods documented
- [ ] Complex logic has comments
- [ ] Type hints serve as documentation

### 12.3 User Documentation
- [ ] User guide for workflow system
- [ ] Examples for each template
- [ ] Tutorial for creating custom workflows
- [ ] API reference for Python API
- [ ] Troubleshooting guide

### 12.4 CHANGELOG
- [ ] CHANGELOG.md updated with v1.7.0 entry
- [ ] All features listed
- [ ] Breaking changes noted (if any)
- [ ] Migration guide (if needed)

---

## 13. Integration & Compatibility

### 13.1 Agent System Integration
- [ ] WorkflowExecutor uses AgentManager
- [ ] Agent spawning works correctly
- [ ] Agent results captured properly
- [ ] Agent permissions respected
- [ ] Agent resource limits enforced

### 13.2 Session Integration
- [ ] Workflow state persisted to sessions
- [ ] Workflow results in session history
- [ ] Resume from previous session works

### 13.3 Permission System Integration
- [ ] Workflow execution requires permission
- [ ] Individual agent permissions checked
- [ ] Permission denials handled gracefully

### 13.4 Hook System Integration
- [ ] Workflow lifecycle hooks fire correctly
- [ ] Hook metadata includes workflow info
- [ ] Hook failures don't crash workflow

### 13.5 Command System Integration
- [ ] Workflow commands registered
- [ ] Commands execute correctly
- [ ] Help system includes workflow commands

### 13.6 Tool System Integration
- [ ] WorkflowTool registered
- [ ] Tool accessible to LLM
- [ ] Tool results properly formatted

### 13.7 Backward Compatibility
- [ ] No breaking changes to existing APIs
- [ ] All existing functionality preserved
- [ ] Existing tests still pass
- [ ] Zero migration required

---

## 14. Performance

### 14.1 Execution Performance
- [ ] Workflow startup < 100ms
- [ ] Step transition < 50ms
- [ ] Checkpoint creation < 200ms
- [ ] State restoration < 300ms

### 14.2 Resource Usage
- [ ] No memory leaks
- [ ] Proper resource cleanup
- [ ] File handles closed
- [ ] Connections closed

### 14.3 Scalability
- [ ] Max 20 steps enforced
- [ ] Max 5 parallel steps enforced
- [ ] Large workflows complete successfully
- [ ] Concurrent workflows don't interfere

### 14.4 Concurrency
- [ ] Thread-safe state management
- [ ] No race conditions
- [ ] Parallel execution works correctly
- [ ] Proper lock usage

---

## 15. Error Handling & Robustness

### 15.1 Validation Errors
- [ ] Invalid workflow definitions rejected
- [ ] Clear error messages for syntax errors
- [ ] Clear error messages for semantic errors
- [ ] Validation happens before execution

### 15.2 Runtime Errors
- [ ] Agent failures handled gracefully
- [ ] Step failures recorded correctly
- [ ] Workflow failure propagated correctly
- [ ] Partial results preserved

### 15.3 Recovery
- [ ] Failed workflows can be resumed
- [ ] Checkpoints enable recovery
- [ ] State restoration works correctly
- [ ] Resume skips completed steps

### 15.4 Edge Cases
- [ ] Empty workflows handled
- [ ] Single-step workflows work
- [ ] All steps fail scenario
- [ ] All steps skipped scenario
- [ ] Timeout scenarios

---

## 16. Security

### 16.1 Input Validation
- [ ] Workflow definitions validated
- [ ] Condition expressions sanitized
- [ ] No code injection via conditions
- [ ] NO use of eval() or exec()

### 16.2 Permission Checks
- [ ] Workflow execution gated by permissions
- [ ] Agent permissions still apply
- [ ] Restricted operations require approval

### 16.3 Resource Limits
- [ ] Max steps prevents abuse
- [ ] Max parallel prevents exhaustion
- [ ] Timeout prevents hanging
- [ ] Agent limits still enforced

### 16.4 Error Messages
- [ ] No sensitive data in errors
- [ ] No stack traces exposed to users
- [ ] Clear, safe error messages

---

## 17. Final Verification

### 17.1 Full Test Suite
```bash
pytest tests/ -v --cov=src/code_forge/workflows --cov-fail-under=90
```
- [ ] Exit code 0
- [ ] All tests pass
- [ ] Coverage ≥ 90%
- [ ] No warnings

### 17.2 Type Checking
```bash
mypy src/code_forge/workflows/
```
- [ ] Exit code 0
- [ ] No type errors

### 17.3 Linting
```bash
ruff check src/code_forge/workflows/
```
- [ ] Exit code 0
- [ ] No style violations

### 17.4 Manual Verification
Execute all 7 built-in templates:
- [ ] `pr_review` workflow completes successfully
- [ ] `bug_fix` workflow completes successfully
- [ ] `feature_impl` workflow completes successfully
- [ ] `security_audit` workflow completes successfully
- [ ] `code_quality` workflow completes successfully
- [ ] `migration` workflow completes successfully
- [ ] `parallel_analysis` workflow completes successfully

### 17.5 Command Verification
- [ ] `/workflow list` shows all templates
- [ ] `/workflow run pr_review` executes workflow
- [ ] `/workflow status <id>` shows status
- [ ] `/workflow resume <id>` resumes (if implemented)
- [ ] `/workflow cancel <id>` cancels (if implemented)

---

## 18. Version and Release

### 18.1 Version Bump
- [ ] `pyproject.toml` version → 1.7.0
- [ ] `src/code_forge/__init__.py` __version__ → 1.7.0
- [ ] `.ai/START.md` version → 1.7.0

### 18.2 Changelog
- [ ] CHANGELOG.md has entry for v1.7.0
- [ ] Entry date is set
- [ ] All features documented
- [ ] Formatted correctly

### 18.3 Git Commit
- [ ] All changes committed
- [ ] Commit message follows conventions
- [ ] No uncommitted changes
- [ ] Planning docs committed

---

## Phase Complete When

**ALL checkboxes above are checked** and:

1. Workflow system fully implemented
2. All 7 built-in templates working
3. All tests pass (unit, integration, system)
4. Test coverage ≥ 90%
5. No regressions in existing functionality
6. Code quality checks pass (mypy, ruff)
7. Documentation complete
8. Version bumped to 1.7.0
9. CHANGELOG updated
10. All planning documents complete

---

## Sign-Off

When all criteria are met:

**Implementer:** ___________________ Date: ___________
**Reviewer:** _____________________ Date: ___________

Phase status: ⬜ Planning ⬜ In Progress ⬜ Complete
