# Agent Workflow System: Code Review Checklist

**Phase:** agent-workflows
**Version Target:** 1.7.0
**Created:** 2025-12-21

Comprehensive code review checklist and quality gates for workflow system implementation.

---

## Review Philosophy

### Goals
- **Correctness:** Code does what it's supposed to
- **Quality:** Code meets standards
- **Maintainability:** Code is easy to understand and modify
- **Security:** Code has no vulnerabilities
- **Performance:** Code is reasonably efficient
- **Integration:** Code works with existing systems

### Review Process
1. **Self-Review:** Author reviews own code before requesting review
2. **Automated Review:** CI checks (tests, types, linting)
3. **Peer Review:** Another developer reviews the code
4. **Final Review:** Before merge to main

---

## Pre-Review Automated Checks

### Must Pass Before Human Review

```bash
# Type checking
mypy src/code_forge/workflows/
# Exit code 0, no type errors

# Linting
ruff check src/code_forge/workflows/
# Exit code 0, no violations

# Unit tests
pytest tests/unit/workflows/ -v
# All pass, coverage ≥ 90%

# Integration tests
pytest tests/integration/workflows/ -v
# All pass

# Full test suite
pytest tests/ -v
# All pass, no regressions
```

**Gate:** ❌ If any automated check fails, code is not ready for review

---

## Component-Specific Review Checklists

### 1. Models (models.py)

**Data Model Quality:**
- [ ] All models use @dataclass or Pydantic BaseModel
- [ ] All fields have type hints
- [ ] All fields have docstrings (if not obvious)
- [ ] Required vs optional fields correctly specified
- [ ] Default values are immutable (no mutable defaults)
- [ ] Validation methods exist where needed
- [ ] Models are serializable to JSON
- [ ] Models can be deserialized from JSON
- [ ] Equality comparison implemented correctly

**Specific Models:**
- [ ] WorkflowDefinition: Complete and accurate
- [ ] WorkflowStep: All fields make sense
- [ ] WorkflowState: State transitions valid
- [ ] StepResult: Captures all necessary data
- [ ] WorkflowResult: Properly aggregates step results
- [ ] WorkflowStatus enum: Complete set of states

**Error Handling:**
- [ ] Validation errors have clear messages
- [ ] Type errors caught early
- [ ] Serialization errors handled gracefully

---

### 2. Graph (graph.py)

**Graph Construction:**
- [ ] WorkflowGraph uses adjacency list representation
- [ ] Adding nodes is O(1)
- [ ] Adding edges is O(1)
- [ ] Graph is immutable after construction
- [ ] No memory leaks
- [ ] Thread-safe if needed

**Cycle Detection:**
- [ ] Uses DFS-based algorithm
- [ ] Detects all cycles (simple, self-reference, complex)
- [ ] Returns cycle path for debugging
- [ ] O(V + E) time complexity
- [ ] Clear error messages with cycle path

**Topological Sort:**
- [ ] Returns valid execution order
- [ ] Handles disconnected components
- [ ] Fails gracefully on cyclic graphs
- [ ] O(V + E) time complexity
- [ ] Deterministic output (given same input)

**Validation:**
- [ ] All referenced agents exist
- [ ] All referenced steps exist
- [ ] No orphaned steps
- [ ] Parallel hints are valid
- [ ] Clear error messages for all failures

**Code Quality:**
- [ ] Clear variable names
- [ ] Appropriate comments for complex logic
- [ ] No magic numbers
- [ ] Proper use of data structures

---

### 3. Parser (parser.py)

**YAML Parser:**
- [ ] Uses PyYAML safely (no unsafe loading)
- [ ] Schema validation with Pydantic or similar
- [ ] Clear error messages with line numbers
- [ ] Handles all workflow features
- [ ] Rejects invalid YAML gracefully
- [ ] File and string parsing both work
- [ ] UTF-8 encoding handled correctly

**Python API:**
- [ ] Fluent interface design
- [ ] Method chaining works correctly
- [ ] Validation during construction
- [ ] Produces same result as YAML
- [ ] Clear method names
- [ ] Good docstrings

**Error Handling:**
- [ ] Syntax errors identified clearly
- [ ] Missing fields reported with field name
- [ ] Type errors have helpful messages
- [ ] File not found handled gracefully

**Code Quality:**
- [ ] No code duplication
- [ ] Appropriate abstractions
- [ ] Clear separation of concerns
- [ ] Testable design

---

### 4. Conditions (conditions.py)

**Expression Parser:**
- [ ] **CRITICAL: NO eval() or exec()**
- [ ] **CRITICAL: NO ast.literal_eval on user input**
- [ ] Whitelist-based parsing only
- [ ] Recursive descent or similar safe parser
- [ ] Handles all operators correctly
- [ ] Handles field access (dot notation)
- [ ] Rejects unsafe constructs
- [ ] Clear error messages

**Condition Evaluator:**
- [ ] Safely evaluates parsed AST
- [ ] Handles missing fields without crash
- [ ] Handles type mismatches gracefully
- [ ] Returns boolean result
- [ ] Logs warnings for issues
- [ ] No exceptions leak to caller

**Security:**
- [ ] **Cannot execute arbitrary code**
- [ ] **Cannot import modules**
- [ ] **Cannot access __builtins__**
- [ ] **Cannot access file system**
- [ ] Input sanitization where needed

**Code Quality:**
- [ ] Parser logic is clear
- [ ] AST node types well-defined
- [ ] Evaluator logic is simple
- [ ] Good test coverage (especially edge cases)

---

### 5. State Management (state.py)

**StateManager:**
- [ ] Thread-safe state persistence
- [ ] Atomic writes (no partial states)
- [ ] File locking if concurrent access possible
- [ ] Clear file naming convention
- [ ] Proper error handling for I/O
- [ ] State cleanup on completion
- [ ] List states works correctly

**CheckpointManager:**
- [ ] Checkpoints created atomically
- [ ] Checkpoint restoration validates data
- [ ] Checkpoint files organized logically
- [ ] Cleanup of old checkpoints
- [ ] Restoration works correctly
- [ ] Handles missing checkpoints gracefully

**Persistence:**
- [ ] JSON serialization handles all types
- [ ] Deserialization validates structure
- [ ] File paths are safe (no traversal)
- [ ] Proper permissions on files
- [ ] Disk space errors handled

**Code Quality:**
- [ ] Clear file structure
- [ ] Good separation of concerns
- [ ] Appropriate logging
- [ ] Resource cleanup

---

### 6. Executor (executor.py)

**WorkflowExecutor:**
- [ ] Async execution throughout
- [ ] Validates workflow before execution
- [ ] Builds execution plan (topological sort)
- [ ] Tracks state during execution
- [ ] Creates checkpoints after each step
- [ ] Fires lifecycle events
- [ ] Collects WorkflowResult
- [ ] Handles errors gracefully
- [ ] Cleans up resources

**StepExecutor:**
- [ ] Evaluates conditions before execution
- [ ] Waits for dependencies
- [ ] Spawns agent via AgentManager
- [ ] Collects agent result
- [ ] Returns StepResult
- [ ] Handles agent failures
- [ ] Retry logic works correctly
- [ ] Timeout enforcement

**ParallelExecutor:**
- [ ] Uses asyncio.gather correctly
- [ ] Limits concurrent execution
- [ ] Handles partial failures
- [ ] Results collected correctly
- [ ] Thread-safe state updates
- [ ] No deadlocks
- [ ] No race conditions

**Resource Management:**
- [ ] Workflow timeout enforced
- [ ] Max steps limit enforced
- [ ] Max parallel limit enforced
- [ ] Agent resource limits inherited
- [ ] Proper cleanup on failure

**Error Handling:**
- [ ] Agent errors caught
- [ ] Step failures recorded
- [ ] Workflow failures propagated
- [ ] Clear error messages
- [ ] Stack traces logged (not exposed)

**Code Quality:**
- [ ] Complex logic well-commented
- [ ] Clear execution flow
- [ ] Good separation of concerns
- [ ] Testable design (mockable dependencies)

---

### 7. Templates (templates/*.yaml + registry.py)

**Template Files:**
For EACH of 7 templates:
- [ ] Valid YAML syntax
- [ ] Complete metadata (name, description, version, author)
- [ ] Clear step descriptions
- [ ] Appropriate agent types
- [ ] Dependencies correct
- [ ] Conditions valid (if used)
- [ ] Parallel hints appropriate
- [ ] Comments explain purpose

**Template Registry:**
- [ ] Singleton pattern implemented correctly
- [ ] Thread-safe with RLock
- [ ] Discovery from multiple locations
- [ ] Registration validation
- [ ] Retrieval works correctly
- [ ] List returns all templates
- [ ] Clear error messages

**Template Instantiation:**
- [ ] Parameter substitution works
- [ ] Validation after substitution
- [ ] Clear error for missing params
- [ ] Type checking for params

**Code Quality:**
- [ ] Clear template structure
- [ ] Good documentation
- [ ] Examples where helpful

---

### 8. Commands (commands.py)

**WorkflowCommand:**
- [ ] Inherits from Command base class
- [ ] All subcommands implemented:
  - [ ] list
  - [ ] run
  - [ ] status
  - [ ] resume (optional)
  - [ ] cancel (optional)
- [ ] Argument parsing correct
- [ ] Help text is clear
- [ ] Error messages are helpful
- [ ] Permission checks integrated
- [ ] Output formatting appropriate

**Command Execution:**
- [ ] Async execution
- [ ] Returns CommandResult
- [ ] Handles all error cases
- [ ] Progress feedback to user
- [ ] Result display is clear

**Code Quality:**
- [ ] Clear command structure
- [ ] Good separation of concerns
- [ ] Testable (mockable dependencies)

---

### 9. Tool (tool.py)

**WorkflowTool:**
- [ ] Inherits from BaseTool
- [ ] Name is "workflow"
- [ ] Description is clear for LLM
- [ ] Parameters well-defined
- [ ] Execute method is async
- [ ] Returns ToolResult
- [ ] Handles all workflow outcomes
- [ ] Permission integration
- [ ] Registered in ToolRegistry

**Tool Behavior:**
- [ ] LLM can invoke tool
- [ ] Structured results returned
- [ ] Errors handled gracefully
- [ ] Result format is useful

**Code Quality:**
- [ ] Clear implementation
- [ ] Good docstrings
- [ ] Testable design

---

## Integration Review Checklist

### Agent System Integration
- [ ] AgentManager used correctly
- [ ] Agents spawned properly
- [ ] AgentResults collected
- [ ] Agent permissions respected
- [ ] Agent resource limits enforced
- [ ] No breaking changes to agent system

### Session System Integration
- [ ] Workflow state persisted to sessions
- [ ] Session history includes workflows
- [ ] Resume from session works
- [ ] No breaking changes to session system

### Permission System Integration
- [ ] Workflow execution requires permission
- [ ] Agent permissions still apply
- [ ] Permission denials handled
- [ ] No permission bypasses

### Hook System Integration
- [ ] Lifecycle hooks fire correctly
- [ ] Hook metadata is accurate
- [ ] Hook failures don't crash workflow
- [ ] Events include correct data

### Command System Integration
- [ ] Commands registered correctly
- [ ] Help system includes workflows
- [ ] Command parsing works
- [ ] No breaking changes

### Tool System Integration
- [ ] Tool registered correctly
- [ ] Tool accessible to LLM
- [ ] Tool results formatted correctly
- [ ] No breaking changes

---

## Design Pattern Review

### Patterns Applied
- [ ] **Command Pattern:** WorkflowStep encapsulates execution
- [ ] **Template Method:** Executor defines execution algorithm
- [ ] **Factory Pattern:** Workflow creation from YAML/Python
- [ ] **Strategy Pattern:** Different execution strategies
- [ ] **Observer Pattern:** Event-based progress tracking
- [ ] **Singleton Pattern:** Template registry
- [ ] **Composite Pattern:** Workflow as composition of steps
- [ ] **State Pattern:** Workflow state management

### SOLID Principles
- [ ] **Single Responsibility:** Each class has one purpose
- [ ] **Open/Closed:** Easy to extend with new templates
- [ ] **Liskov Substitution:** Workflows interchangeable
- [ ] **Interface Segregation:** Clean interfaces
- [ ] **Dependency Inversion:** Depend on abstractions

---

## Security Review

### Input Validation
- [ ] Workflow definitions validated
- [ ] YAML parsing is safe
- [ ] **Condition expressions cannot execute code**
- [ ] **No eval() or exec() used**
- [ ] File paths validated (no traversal)
- [ ] User input sanitized

### Permission Checks
- [ ] Workflow execution gated
- [ ] Agent permissions enforced
- [ ] No permission bypasses
- [ ] Clear permission prompts

### Resource Limits
- [ ] Max steps enforced
- [ ] Max parallel enforced
- [ ] Timeout enforced
- [ ] Agent limits inherited

### Error Messages
- [ ] No sensitive data leaked
- [ ] No stack traces exposed
- [ ] Safe error messages

### Dependencies
- [ ] No new security vulnerabilities
- [ ] All dependencies up to date
- [ ] No unsafe YAML loading

---

## Performance Review

### Efficiency
- [ ] Workflow startup < 100ms
- [ ] Step transition < 50ms
- [ ] Checkpoint creation < 200ms
- [ ] State restoration < 300ms
- [ ] No O(n²) algorithms where O(n) possible
- [ ] Appropriate data structures used

### Resource Usage
- [ ] No memory leaks
- [ ] Proper resource cleanup
- [ ] File handles closed
- [ ] Async operations don't block

### Scalability
- [ ] Handles 20-step workflows
- [ ] Concurrent workflows don't interfere
- [ ] Linear scaling with workflow size
- [ ] No contention bottlenecks

### Concurrency
- [ ] Thread-safe state management
- [ ] No race conditions
- [ ] No deadlocks
- [ ] Proper use of async/await

---

## Testing Review

### Test Coverage
- [ ] Overall coverage ≥ 90%
- [ ] All critical paths covered
- [ ] Edge cases tested
- [ ] Error paths tested
- [ ] Integration points tested

### Test Quality
- [ ] Tests are independent
- [ ] Clear test names (test_what_when_then)
- [ ] AAA pattern followed
- [ ] Appropriate assertions
- [ ] No flaky tests
- [ ] Fast execution

### Test Completeness
- [ ] Unit tests for all components
- [ ] Integration tests for workflows
- [ ] E2E tests for templates
- [ ] Permission tests
- [ ] Hook tests
- [ ] Error handling tests

---

## Documentation Review

### Code Documentation
- [ ] All modules have docstrings
- [ ] All classes have docstrings
- [ ] All public methods have docstrings
- [ ] Complex logic has comments
- [ ] Type hints are comprehensive

### Planning Documentation
- [ ] PLAN.md complete and accurate
- [ ] COMPLETION_CRITERIA.md comprehensive
- [ ] GHERKIN.md covers all scenarios
- [ ] DEPENDENCIES.md lists all dependencies
- [ ] TESTS.md defines test strategy
- [ ] REVIEW.md (this document) complete

### User Documentation
- [ ] User guide for workflow system
- [ ] Examples for each template
- [ ] Tutorial for custom workflows
- [ ] API reference for Python API
- [ ] Troubleshooting guide

### CHANGELOG
- [ ] v1.7.0 entry added
- [ ] All features listed
- [ ] Breaking changes noted (if any)
- [ ] Migration guide (if needed)

---

## Backward Compatibility Review

### No Breaking Changes
- [ ] All existing APIs unchanged
- [ ] Existing tests still pass
- [ ] Agent system unchanged
- [ ] Session system unchanged
- [ ] Command system unchanged
- [ ] Tool system unchanged

### Additive Changes Only
- [ ] New `/workflow` commands
- [ ] New WorkflowTool
- [ ] New workflow module
- [ ] Templates in new directories

### Migration
- [ ] No migration required
- [ ] Purely opt-in feature
- [ ] Existing code still works

---

## Final Quality Gates

### Must Pass Before Merge

**Automated Checks:**
```bash
# Type checking
mypy src/code_forge/workflows/
# Must: Exit code 0

# Linting
ruff check src/code_forge/workflows/
# Must: Exit code 0

# Tests
pytest tests/ -v --cov=src/code_forge/workflows --cov-fail-under=90
# Must: All pass, coverage ≥ 90%

# No regressions
pytest tests/ -v
# Must: All pass
```

**Manual Verification:**
- [ ] All 7 built-in templates execute successfully
- [ ] Sequential workflows work end-to-end
- [ ] Parallel workflows work end-to-end
- [ ] Conditional workflows work end-to-end
- [ ] Resume from checkpoint works
- [ ] `/workflow list` shows templates
- [ ] `/workflow run <name>` executes workflow
- [ ] `/workflow status <id>` shows status
- [ ] Workflow tool accessible to LLM
- [ ] Permission prompts appear correctly
- [ ] Hooks fire at correct times

**Code Quality:**
- [ ] No TODO comments (or tracked in issues)
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] No hardcoded values
- [ ] Clear variable names
- [ ] Appropriate comments

**Documentation:**
- [ ] All planning docs complete
- [ ] Code documentation complete
- [ ] User documentation complete
- [ ] CHANGELOG updated

---

## Review Sign-Off

### Self-Review Checklist
Author must verify:
- [ ] Read all code changes
- [ ] Ran all automated checks
- [ ] Tested manually
- [ ] Reviewed all checklist items
- [ ] Fixed all issues found
- [ ] Documentation complete

### Peer Review Checklist
Reviewer must verify:
- [ ] Read planning documents
- [ ] Reviewed code changes
- [ ] Checked critical sections
- [ ] Ran tests locally
- [ ] Verified quality gates
- [ ] No security issues
- [ ] Provided feedback

### Final Sign-Off

**Author:** _________________ Date: _________
- [ ] All automated checks pass
- [ ] All manual checks complete
- [ ] All feedback addressed
- [ ] Ready for peer review

**Peer Reviewer:** _________________ Date: _________
- [ ] Code reviewed thoroughly
- [ ] Tests verified
- [ ] Quality gates passed
- [ ] Approve for merge / Request changes

**Final Approver:** _________________ Date: _________
- [ ] All reviews complete
- [ ] All criteria met
- [ ] Approve for merge

**Phase Status:** ⬜ In Review ⬜ Approved ⬜ Merged

---

## Review Metrics

### Target Metrics
- Review time: < 1 day from ready to approved
- Issues found: Document and track
- Code quality score: All gates pass

### What to Look For
**Critical Issues (Block Merge):**
- Security vulnerabilities
- Breaking changes
- Test failures
- Type errors
- Linting errors

**Major Issues (Must Fix):**
- Poor design patterns
- Missing tests
- Incomplete documentation
- Performance problems

**Minor Issues (Should Fix):**
- Code style inconsistencies
- Unclear names
- Missing comments
- Minor refactoring opportunities

---

## Common Issues Checklist

### Prevent These Mistakes
- [ ] Using eval() or exec()
- [ ] Mutable default arguments
- [ ] Not cleaning up resources
- [ ] Leaking exceptions to users
- [ ] Missing error handling
- [ ] Race conditions
- [ ] Deadlocks
- [ ] Memory leaks
- [ ] Breaking changes
- [ ] Missing tests
- [ ] Hardcoded values
- [ ] Poor variable names

---

## Post-Merge Monitoring

After merge, monitor for:
- [ ] Tests still passing in CI
- [ ] No integration issues
- [ ] Performance acceptable
- [ ] No user-reported bugs
- [ ] Documentation accurate

---

This completes the code review checklist. Use this document systematically to ensure high-quality, production-ready code.
