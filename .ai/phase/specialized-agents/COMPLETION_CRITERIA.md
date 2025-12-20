# Specialized Task Agents: Completion Criteria

**Phase:** specialized-agents
**Version Target:** 1.6.0
**Created:** 2025-12-21

All criteria must be met before marking this phase complete.

---

## 1. Agent Type Definitions

### 1.1 Registry Configuration
- [ ] 16 new `AgentTypeDefinition` constants added to `agents/types.py`
- [ ] All 16 agent types have unique names (no duplicates)
- [ ] All 16 agent types have clear descriptions (< 100 characters)
- [ ] All 16 agent types have specialized system prompts (> 200 characters each)
- [ ] All 16 agent types specify tool restrictions appropriate to their domain
- [ ] All 16 agent types have tailored resource limits (tokens, time)
- [ ] `AgentTypeRegistry._register_builtins()` registers all 20 types (4 existing + 16 new)
- [ ] `AgentTypeRegistry.list_types()` returns exactly 20 agent types

### 1.2 Tool Access Configuration
Verify each agent type has correct default tools:
- [ ] `test-generation`: ["glob", "grep", "read", "write"]
- [ ] `documentation`: ["glob", "grep", "read", "write"]
- [ ] `refactoring`: ["glob", "grep", "read", "write", "edit"]
- [ ] `debug`: ["glob", "grep", "read", "bash"]
- [ ] `writing`: ["read", "write", "web-search", "web-fetch"]
- [ ] `communication`: ["read", "write", "git", "github"]
- [ ] `tutorial`: ["glob", "grep", "read", "write", "web-search"]
- [ ] `diagram`: ["glob", "grep", "read", "write"]
- [ ] `qa-manual`: ["read", "write", "bash"]
- [ ] `research`: ["web-search", "web-fetch", "read", "write"]
- [ ] `log-analysis`: ["read", "grep", "bash", "write"]
- [ ] `performance-analysis`: ["read", "bash", "grep", "write"]
- [ ] `security-audit`: ["glob", "grep", "read", "bash", "write"]
- [ ] `dependency-analysis`: ["read", "bash", "web-search", "write"]
- [ ] `migration-planning`: ["glob", "grep", "read", "write", "bash"]
- [ ] `configuration`: ["glob", "read", "write", "edit"]

### 1.3 Resource Limits Configuration
Verify each agent type has correct limits:
- [ ] `test-generation`: 40000 tokens, 300s
- [ ] `documentation`: 35000 tokens, 240s
- [ ] `refactoring`: 45000 tokens, 360s
- [ ] `debug`: 30000 tokens, 240s
- [ ] `writing`: 40000 tokens, 300s
- [ ] `communication`: 25000 tokens, 180s
- [ ] `tutorial`: 45000 tokens, 360s
- [ ] `diagram`: 30000 tokens, 240s
- [ ] `qa-manual`: 35000 tokens, 300s
- [ ] `research`: 50000 tokens, 400s
- [ ] `log-analysis`: 40000 tokens, 300s
- [ ] `performance-analysis`: 35000 tokens, 300s
- [ ] `security-audit`: 45000 tokens, 360s
- [ ] `dependency-analysis`: 35000 tokens, 300s
- [ ] `migration-planning`: 50000 tokens, 400s
- [ ] `configuration`: 30000 tokens, 240s

---

## 2. Agent Implementations

### 2.1 File Structure
- [ ] 16 new agent implementation files created in `agents/builtin/`
- [ ] All files follow naming convention: `snake_case.py`
- [ ] Each file has module-level docstring
- [ ] Each file imports required base classes from `agents.base`

### 2.2 Class Implementation
For EACH of the 16 new agents:
- [ ] Class inherits from `Agent` base class
- [ ] Class name follows convention: `{Type}Agent` (e.g., `TestGenerationAgent`)
- [ ] `agent_type` property implemented and returns correct string
- [ ] `execute()` method implemented and is async
- [ ] Class has comprehensive docstring describing purpose
- [ ] Implementation follows existing patterns (e.g., `ExploreAgent`, `PlanAgent`)

### 2.3 Module Exports
- [ ] `agents/builtin/__init__.py` imports all 20 agent classes
- [ ] `__all__` list contains all 20 agent class names
- [ ] Imports and exports are alphabetically sorted
- [ ] No import errors when importing from `agents.builtin`

---

## 3. System Prompts

For EACH of the 16 new agent types, verify prompt contains:
- [ ] Clear role definition ("You are a [TYPE] agent specialized in...")
- [ ] Primary goal statement
- [ ] Numbered guidelines (minimum 5)
- [ ] Expected output structure
- [ ] Domain-specific best practices
- [ ] Minimum prompt length: 200 characters
- [ ] Maximum prompt length: 2000 characters
- [ ] Prompt is clear, actionable, and unambiguous

---

## 4. Testing

### 4.1 Unit Tests - Agent Types
- [ ] Test file `tests/unit/agents/test_types.py` exists
- [ ] Test verifies 20 agent types registered
- [ ] Test verifies each new agent type exists
- [ ] Test verifies correct descriptions
- [ ] Test verifies correct default tools
- [ ] Test verifies correct resource limits
- [ ] Test verifies no duplicate registrations allowed
- [ ] All tests pass

### 4.2 Unit Tests - Agent Implementations
For EACH of the 16 new agents:
- [ ] Test file `tests/unit/agents/builtin/test_{agent_name}.py` exists
- [ ] Test verifies agent initialization
- [ ] Test verifies `agent_type` property
- [ ] Test verifies correct tool restrictions
- [ ] Test verifies state management
- [ ] All tests pass

### 4.3 Integration Tests
- [ ] Test file `tests/integration/test_all_specialized_agents.py` exists
- [ ] Test verifies end-to-end execution for each agent type
- [ ] Test verifies tool restrictions enforced
- [ ] Test verifies resource limits respected
- [ ] Test verifies permission system integration
- [ ] Test verifies hook system integration
- [ ] Test verifies concurrent execution works
- [ ] All tests pass

### 4.4 Test Coverage
- [ ] New code has >90% test coverage
- [ ] No regression in overall project coverage
- [ ] All critical paths tested
- [ ] Edge cases covered

### 4.5 Existing Tests
- [ ] ALL existing tests still pass (zero regressions)
- [ ] No breaking changes to existing agent types
- [ ] Existing agent functionality unchanged

---

## 5. Code Quality

### 5.1 Type Hints
- [ ] All functions have type hints for parameters
- [ ] All functions have type hints for return values
- [ ] No `Any` types unless absolutely necessary
- [ ] Type hints are accurate and complete

### 5.2 Docstrings
- [ ] All modules have docstrings
- [ ] All classes have docstrings (Google style)
- [ ] All public methods have docstrings
- [ ] Docstrings include parameter descriptions
- [ ] Docstrings include return value descriptions
- [ ] Docstrings include raised exceptions

### 5.3 Code Style
- [ ] Code follows PEP 8
- [ ] `ruff check src/code_forge/agents/` passes with no errors
- [ ] `mypy src/code_forge/agents/` passes with no errors
- [ ] No unused imports
- [ ] No unused variables
- [ ] Line length ≤ 100 characters

### 5.4 Design Patterns
- [ ] All agents follow Template Method pattern (inherit from Agent)
- [ ] Factory pattern used correctly (AgentConfig.for_type())
- [ ] Singleton pattern maintained (AgentTypeRegistry)
- [ ] Strategy pattern applied (each agent = different strategy)
- [ ] SOLID principles followed
- [ ] No code duplication
- [ ] Clear separation of concerns

---

## 6. Integration

### 6.1 Agent Factory
- [ ] `AgentConfig.for_type()` works for all 16 new types
- [ ] Factory creates correct configurations
- [ ] Config overrides work correctly
- [ ] Unknown agent types handled gracefully

### 6.2 Tool System Integration
- [ ] Tool restrictions are enforced
- [ ] Restricted tools return clear errors
- [ ] Tool execution logs correctly
- [ ] Permission system intercepts tool calls

### 6.3 Resource Management
- [ ] Token limits enforced correctly
- [ ] Time limits enforced correctly
- [ ] Tool call limits enforced correctly
- [ ] Usage tracking works accurately
- [ ] Limit violations produce clear errors

### 6.4 Hook System Integration
- [ ] Agents fire hooks for tool execution
- [ ] Hook events contain correct metadata
- [ ] Hooks can modify agent behavior
- [ ] Hook failures handled gracefully

### 6.5 Session Integration
- [ ] Agent messages recorded in session
- [ ] Agent results persisted correctly
- [ ] Session history includes agent activity
- [ ] Session serialization works

---

## 7. Error Handling

### 7.1 Tool Errors
- [ ] Tool execution errors handled gracefully
- [ ] Clear error messages returned
- [ ] Agents don't crash on tool errors
- [ ] Errors logged appropriately

### 7.2 LLM Errors
- [ ] LLM API errors handled with retry
- [ ] Backoff strategy implemented
- [ ] Retry failures produce clear errors
- [ ] Errors don't leak sensitive data

### 7.3 Resource Limits
- [ ] Token limit violations produce clear errors
- [ ] Time limit violations handled cleanly
- [ ] Tool call limit violations detected
- [ ] Iteration limit violations detected
- [ ] All limit errors include current usage

### 7.4 State Management
- [ ] Invalid state transitions prevented
- [ ] State changes logged
- [ ] Concurrent access handled correctly
- [ ] Cancellation works correctly

---

## 8. Documentation

### 8.1 Planning Documents
- [x] PLAN.md - Complete and comprehensive
- [x] GHERKIN.md - All scenarios defined
- [x] COMPLETION_CRITERIA.md - This document
- [ ] DEPENDENCIES.md - Dependencies documented
- [ ] TESTS.md - Test strategy defined
- [ ] REVIEW.md - Review checklist created

### 8.2 Code Documentation
- [ ] All new modules have docstrings
- [ ] All new classes have docstrings
- [ ] All new methods have docstrings
- [ ] Complex logic has inline comments
- [ ] Type hints serve as documentation

### 8.3 CHANGELOG
- [ ] CHANGELOG.md updated with v1.6.0 entry
- [ ] All 16 new agent types listed
- [ ] Breaking changes noted (if any)
- [ ] Migration guide provided (if needed)

### 8.4 User Documentation
- [ ] README mentions specialized agents (if appropriate)
- [ ] Agent types listed in user docs
- [ ] Examples provided for common use cases
- [ ] Limitations documented

---

## 9. Performance

### 9.1 Resource Usage
- [ ] Agent initialization is fast (< 100ms)
- [ ] Type registry lookup is O(1)
- [ ] No memory leaks detected
- [ ] Resource usage scales linearly with agents

### 9.2 Concurrent Execution
- [ ] Multiple agents run without interference
- [ ] No race conditions detected
- [ ] Thread safety maintained
- [ ] Lock contention minimized

---

## 10. Backward Compatibility

### 10.1 No Breaking Changes
- [ ] All 4 existing agent types unchanged
- [ ] Existing agent functionality preserved
- [ ] AgentConfig API unchanged
- [ ] AgentTypeRegistry API unchanged (except additions)
- [ ] All existing code still works

### 10.2 Migration
- [ ] No migration needed for existing code
- [ ] New agents are purely additive
- [ ] Existing configurations still valid

---

## 11. Final Verification

### 11.1 Full Test Suite
```bash
pytest tests/ -v
```
- [ ] Exit code 0 (all tests pass)
- [ ] No failures
- [ ] No errors
- [ ] No warnings (or acceptable warnings documented)
- [ ] Coverage >90%

### 11.2 Type Checking
```bash
mypy src/code_forge/
```
- [ ] Exit code 0 (no type errors)
- [ ] No errors in new code
- [ ] No new errors in existing code

### 11.3 Linting
```bash
ruff check src/code_forge/
```
- [ ] Exit code 0 (no lint errors)
- [ ] No style violations
- [ ] No complexity violations
- [ ] No security issues

### 11.4 Registry Verification
Python verification:
```python
from code_forge.agents.types import AgentTypeRegistry
registry = AgentTypeRegistry.get_instance()
assert len(registry.list_types()) == 20
assert "test-generation" in registry.list_types()
assert "research" in registry.list_types()
# ... verify all 16 new types
```
- [ ] Verification script passes

### 11.5 Integration Smoke Test
- [ ] Create agent of each new type
- [ ] Execute simple task with each
- [ ] Verify all complete successfully
- [ ] No crashes or exceptions

---

## 12. Version and Release

### 12.1 Version Bump
- [ ] `pyproject.toml` version updated to 1.6.0
- [ ] `src/code_forge/__init__.py` `__version__` updated to 1.6.0
- [ ] `.ai/START.md` version updated to 1.6.0

### 12.2 Changelog
- [ ] CHANGELOG.md has entry for v1.6.0
- [ ] Entry date is set
- [ ] All changes documented
- [ ] Formatted correctly

### 12.3 Git Commit
- [ ] All changes committed
- [ ] Commit message follows conventions
- [ ] No uncommitted changes
- [ ] No merge conflicts

---

## Phase Complete When

**ALL checkboxes above are checked** and:

1. AgentTypeRegistry lists exactly 20 agent types
2. All 16 new agent implementations exist and work
3. All tests pass (unit, integration, system)
4. Test coverage >90%
5. No regressions in existing functionality
6. Code quality checks pass (mypy, ruff)
7. Documentation complete
8. Version bumped to 1.6.0
9. CHANGELOG updated
10. All planning documents complete

---

## Sign-Off

When all criteria are met:

**Implementer:** ___________________ Date: ___________
**Reviewer:** _____________________ Date: ___________

Phase status: ⬜ Planning ⬜ In Progress ⬜ Complete
