# Specialized Task Agents: Code Review Checklist

**Phase:** specialized-agents
**Version Target:** 1.6.0
**Created:** 2025-12-21

Comprehensive code review checklist and quality gates.

---

## 1. Review Philosophy

### 1.1 Goals of Code Review
- **Correctness:** Code does what it's supposed to
- **Quality:** Code meets standards
- **Maintainability:** Code is easy to understand and modify
- **Security:** Code has no vulnerabilities
- **Performance:** Code is reasonably efficient
- **Consistency:** Code follows project conventions

### 1.2 Review Types
1. **Self-Review:** Author reviews own code before requesting review
2. **Peer Review:** Another developer reviews the code
3. **Automated Review:** Tools check code quality
4. **Final Review:** Before merge to main

---

## 2. Pre-Review Checklist

Before requesting review, author must verify:
- [ ] All tests pass locally
- [ ] Code coverage ≥ 90%
- [ ] `mypy` passes with no errors
- [ ] `ruff` passes with no errors
- [ ] Self-reviewed all changes
- [ ] Commit messages are clear
- [ ] Documentation updated
- [ ] CHANGELOG updated

---

## 3. Automated Quality Gates

### 3.1 Static Analysis

**Type Checking:**
```bash
mypy src/code_forge/agents/
```
- [ ] Exit code 0
- [ ] No type errors
- [ ] No `# type: ignore` comments (unless justified)
- [ ] All functions have type hints

**Linting:**
```bash
ruff check src/code_forge/agents/
```
- [ ] Exit code 0
- [ ] No style violations
- [ ] No complexity violations (McCabe < 10)
- [ ] No security issues flagged

**Code Formatting:**
```bash
ruff format --check src/code_forge/agents/
```
- [ ] Exit code 0
- [ ] All code formatted consistently

### 3.2 Testing

**Unit Tests:**
```bash
pytest tests/unit/agents/ -v --cov=src/code_forge/agents --cov-fail-under=90
```
- [ ] All tests pass
- [ ] Coverage ≥ 90%
- [ ] No flaky tests
- [ ] No skipped tests (or justified)

**Integration Tests:**
```bash
pytest tests/integration/ -v
```
- [ ] All tests pass
- [ ] No integration failures

**Full Test Suite:**
```bash
pytest tests/ -v
```
- [ ] All tests pass
- [ ] Zero regressions

---

## 4. Code Quality Checklist

### 4.1 Design Patterns

**Template Method Pattern:**
- [ ] All agents inherit from `Agent` base class
- [ ] `agent_type` property implemented
- [ ] `execute()` method implemented as async
- [ ] No overriding of base class internals

**Factory Pattern:**
- [ ] `AgentConfig.for_type()` used correctly
- [ ] No manual config construction in tests
- [ ] Config overrides work properly

**Singleton Pattern:**
- [ ] `AgentTypeRegistry` maintains singleton
- [ ] Thread-safe with `RLock`
- [ ] `get_instance()` returns same instance

**Strategy Pattern:**
- [ ] Each agent type encapsulates different strategy
- [ ] Agents are interchangeable via polymorphism
- [ ] No conditional logic based on agent type

### 4.2 SOLID Principles

**Single Responsibility:**
- [ ] Each agent has one clear purpose
- [ ] Each class has one reason to change
- [ ] No God objects

**Open/Closed:**
- [ ] New agents added without modifying base classes
- [ ] Extension points clearly defined
- [ ] No modification of existing agent types

**Liskov Substitution:**
- [ ] All agents substitutable for Agent base class
- [ ] No surprising behavior in subclasses
- [ ] Contracts honored

**Interface Segregation:**
- [ ] Agents implement only what they need
- [ ] No fat interfaces
- [ ] Clear separation of concerns

**Dependency Inversion:**
- [ ] Agents depend on abstractions (Agent base)
- [ ] Not dependent on concrete implementations
- [ ] Dependency injection where appropriate

### 4.3 Code Smells

Check for and eliminate:
- [ ] **Duplicate Code:** No copy-paste programming
- [ ] **Long Methods:** Methods < 50 lines
- [ ] **Long Classes:** Classes < 300 lines
- [ ] **Large Parameter Lists:** < 5 parameters
- [ ] **Feature Envy:** Methods use own class data
- [ ] **Data Clumps:** Related data grouped
- [ ] **Primitive Obsession:** Use domain objects
- [ ] **Comments:** Code explains itself, comments only for why
- [ ] **Dead Code:** No unused code
- [ ] **Speculative Generality:** No premature abstraction

---

## 5. Per-File Review Checklist

### 5.1 agents/types.py

**AgentTypeDefinition Constants:**
For EACH of 16 new agent types:
- [ ] Constant name in SCREAMING_SNAKE_CASE
- [ ] `name` is kebab-case and unique
- [ ] `description` is clear and concise (< 100 chars)
- [ ] `prompt_template` is comprehensive (> 200 chars)
- [ ] `default_tools` is appropriate for agent purpose
- [ ] `default_max_tokens` is reasonable
- [ ] `default_max_time` is reasonable
- [ ] No typos in any field

**Registry Updates:**
- [ ] `_register_builtins()` registers all 16 new types
- [ ] All types in alphabetical order (optional)
- [ ] No duplicates

**Prompt Quality:**
For EACH prompt template:
- [ ] Clear role definition
- [ ] Specific task description
- [ ] Numbered guidelines (minimum 5)
- [ ] Expected output structure
- [ ] Domain-specific best practices
- [ ] No ambiguity
- [ ] Professional tone
- [ ] Correct grammar and spelling

### 5.2 agents/builtin/{agent_name}.py

For EACH of 16 new agent files:

**Module Structure:**
- [ ] Module-level docstring
- [ ] Imports organized (stdlib, third-party, local)
- [ ] No unused imports
- [ ] No wildcard imports

**Class Definition:**
- [ ] Class name is `{Type}Agent` format
- [ ] Class inherits from `Agent`
- [ ] Class has comprehensive docstring
- [ ] Docstring includes purpose, responsibilities, examples

**agent_type Property:**
- [ ] Property decorator used
- [ ] Returns correct string literal
- [ ] Matches type registered in types.py
- [ ] Type hint `-> str`

**execute() Method:**
- [ ] Async method
- [ ] Type hints: `async def execute(self) -> AgentResult`
- [ ] Docstring explains behavior
- [ ] Proper error handling
- [ ] Resource tracking
- [ ] State management
- [ ] Returns AgentResult

**Code Quality:**
- [ ] No hardcoded values (use config)
- [ ] No magic numbers
- [ ] Clear variable names
- [ ] Appropriate comments (only for non-obvious logic)
- [ ] Proper logging
- [ ] Exception handling

### 5.3 agents/builtin/__init__.py

**Exports:**
- [ ] All 20 agents imported (4 existing + 16 new)
- [ ] Imports alphabetically sorted
- [ ] `__all__` list includes all 20 names
- [ ] `__all__` alphabetically sorted
- [ ] No import errors

---

## 6. Test Review Checklist

### 6.1 Unit Test Quality

For EACH test file:

**Test Organization:**
- [ ] Tests organized in classes (if appropriate)
- [ ] Clear test class names
- [ ] Logical grouping of related tests
- [ ] AAA pattern (Arrange, Act, Assert)

**Test Names:**
- [ ] Descriptive test names (`test_what_when_then`)
- [ ] Names indicate what is being tested
- [ ] Names indicate expected behavior
- [ ] No generic names like `test_1`, `test_basic`

**Test Quality:**
- [ ] One assertion per test (or closely related assertions)
- [ ] Tests are independent
- [ ] No test interdependencies
- [ ] Tests clean up after themselves
- [ ] No sleeps or waits (use mocks)
- [ ] Fast execution (< 1s per test)

**Mocking:**
- [ ] Appropriate use of mocks
- [ ] Not mocking what we're testing
- [ ] Mock external dependencies
- [ ] Clear mock setup
- [ ] Mocks verified where appropriate

**Assertions:**
- [ ] Clear, specific assertions
- [ ] Descriptive assertion messages
- [ ] Testing actual behavior, not implementation
- [ ] Both positive and negative cases tested

**Coverage:**
- [ ] All code paths covered
- [ ] Edge cases tested
- [ ] Error cases tested
- [ ] Happy path tested

### 6.2 Integration Test Quality

**Integration Points:**
- [ ] All integration points tested
- [ ] Real components used (minimal mocking)
- [ ] Cross-component interactions verified
- [ ] Error propagation tested

**Scenarios:**
- [ ] Realistic scenarios
- [ ] Cover common use cases
- [ ] Test failure modes
- [ ] Test concurrent execution

---

## 7. Documentation Review Checklist

### 7.1 Code Documentation

**Module Docstrings:**
- [ ] Every module has docstring
- [ ] Docstring describes module purpose
- [ ] Docstring lists main exports
- [ ] Proper formatting

**Class Docstrings:**
- [ ] Every class has docstring
- [ ] Google style format
- [ ] Describes class purpose
- [ ] Lists key attributes (if public)
- [ ] Includes usage example (if complex)

**Method Docstrings:**
- [ ] All public methods have docstrings
- [ ] Args section lists all parameters
- [ ] Returns section describes return value
- [ ] Raises section lists exceptions
- [ ] Examples for complex methods

**Type Hints:**
- [ ] All functions have parameter type hints
- [ ] All functions have return type hints
- [ ] Type hints are accurate
- [ ] No unnecessary `Any` types
- [ ] Generic types used appropriately

### 7.2 Planning Documentation

**Completeness:**
- [x] PLAN.md - Complete and accurate
- [x] GHERKIN.md - All scenarios defined
- [x] COMPLETION_CRITERIA.md - All criteria listed
- [x] DEPENDENCIES.md - All dependencies documented
- [x] TESTS.md - Test strategy defined
- [x] REVIEW.md - This document

**Quality:**
- [ ] No typos or grammatical errors
- [ ] Clear and concise writing
- [ ] Proper formatting (markdown)
- [ ] Accurate information
- [ ] Up-to-date (reflects current implementation)

### 7.3 CHANGELOG

**Entry Format:**
```markdown
## [1.6.0] - 2025-MM-DD

### Added
- 16 new specialized agent types:
  - Coding agents: test-generation, documentation, refactoring, debug
  - Writing agents: writing, communication, tutorial
  - Visual agents: diagram
  - QA agents: qa-manual
  - Research agents: research, log-analysis, performance-analysis
  - Security agents: security-audit, dependency-analysis
  - Project agents: migration-planning, configuration

### Changed
- AgentTypeRegistry now includes 20 agent types (up from 4)

### Fixed
- (Any bug fixes)
```

**Checklist:**
- [ ] Version number correct (1.6.0)
- [ ] Date set
- [ ] All changes listed
- [ ] Organized by Added/Changed/Fixed/Removed
- [ ] User-facing language (not technical internals)
- [ ] Breaking changes highlighted (if any)

---

## 8. Security Review Checklist

### 8.1 Code Security

**Input Validation:**
- [ ] All user input validated
- [ ] No SQL injection risks
- [ ] No command injection risks
- [ ] No path traversal risks
- [ ] No XSS risks

**Secrets Management:**
- [ ] No hardcoded secrets
- [ ] No secrets in logs
- [ ] API keys from environment
- [ ] Sensitive data not exposed in errors

**Error Handling:**
- [ ] Errors don't leak system information
- [ ] Stack traces not exposed to users
- [ ] Error messages are safe
- [ ] Proper exception handling

**Dependencies:**
- [ ] No new dependencies with known vulnerabilities
- [ ] All dependencies up to date
- [ ] Minimal dependency footprint

### 8.2 Agent-Specific Security

**Tool Restrictions:**
- [ ] Agents have minimal required tools
- [ ] No unrestricted bash access (unless required)
- [ ] File system access limited
- [ ] Network access controlled

**Resource Limits:**
- [ ] Token limits prevent abuse
- [ ] Time limits prevent hanging
- [ ] Tool call limits prevent loops
- [ ] Iteration limits prevent infinite loops

**Permission Integration:**
- [ ] Restricted operations require permission
- [ ] Permission checks not bypassable
- [ ] Clear permission prompts

---

## 9. Performance Review Checklist

### 9.1 Efficiency

**Algorithmic Complexity:**
- [ ] No unnecessarily complex algorithms
- [ ] Appropriate data structures used
- [ ] No O(n²) where O(n) possible
- [ ] Registry lookups are O(1)

**Resource Usage:**
- [ ] No memory leaks
- [ ] Proper resource cleanup
- [ ] File handles closed
- [ ] Connections closed

**Concurrency:**
- [ ] Thread-safe where required
- [ ] No race conditions
- [ ] Locks used appropriately
- [ ] No deadlocks

### 9.2 Scalability

**Agent Creation:**
- [ ] Fast initialization (< 100ms)
- [ ] Minimal memory footprint
- [ ] No global state pollution

**Concurrent Execution:**
- [ ] Multiple agents run independently
- [ ] No contention
- [ ] Linear scaling

---

## 10. Maintainability Review Checklist

### 10.1 Code Readability

**Naming:**
- [ ] Clear, descriptive names
- [ ] Consistent naming conventions
- [ ] No abbreviations (unless standard)
- [ ] Names reflect purpose

**Structure:**
- [ ] Logical code organization
- [ ] Clear separation of concerns
- [ ] Appropriate abstraction levels
- [ ] No deep nesting (< 4 levels)

**Comments:**
- [ ] Comments explain "why", not "what"
- [ ] No commented-out code
- [ ] No TODO comments (unless tracked)
- [ ] No misleading comments

### 10.2 Extensibility

**Design:**
- [ ] Easy to add new agent types
- [ ] Clear extension points
- [ ] No hardcoded limitations
- [ ] Plugin-friendly design

**Coupling:**
- [ ] Low coupling between agents
- [ ] Clear interfaces
- [ ] Minimal dependencies
- [ ] No circular dependencies

---

## 11. Consistency Review Checklist

### 11.1 Project Conventions

**Code Style:**
- [ ] Follows PEP 8
- [ ] Consistent with existing code
- [ ] Line length ≤ 100 characters
- [ ] Proper indentation (4 spaces)

**Patterns:**
- [ ] Follows existing patterns
- [ ] Uses project abstractions
- [ ] Consistent error handling
- [ ] Consistent logging

**Testing:**
- [ ] Test style matches existing tests
- [ ] Uses shared fixtures
- [ ] Follows naming conventions
- [ ] Consistent assertions

### 11.2 Documentation Style

**Docstrings:**
- [ ] Google style (project standard)
- [ ] Consistent formatting
- [ ] Complete information
- [ ] Professional tone

**Comments:**
- [ ] Consistent style
- [ ] Appropriate detail level
- [ ] No redundant comments
- [ ] Clear and concise

---

## 12. Backward Compatibility Review

### 12.1 No Breaking Changes

**Existing APIs:**
- [ ] All existing APIs unchanged
- [ ] Existing tests still pass
- [ ] Existing agent types unchanged
- [ ] Existing functionality preserved

**Registry API:**
- [ ] `get_instance()` works as before
- [ ] `get(type_name)` works as before
- [ ] `list_types()` includes existing types
- [ ] New methods are additive only

**Agent Base Classes:**
- [ ] No changes to base class contracts
- [ ] Subclasses still work
- [ ] No new required abstract methods
- [ ] Backward compatible

### 12.2 Migration Path

**If Breaking Changes:**
- [ ] Migration guide provided
- [ ] Deprecated features marked
- [ ] Warnings added
- [ ] Timeline communicated

**For This Phase:**
- [ ] No breaking changes
- [ ] No migration needed
- [ ] Purely additive

---

## 13. Final Review Checklist

### 13.1 Completeness

**Implementation:**
- [ ] All 16 agent types implemented
- [ ] All agents registered
- [ ] All agents exported
- [ ] All functionality working

**Testing:**
- [ ] All tests written
- [ ] All tests passing
- [ ] Coverage ≥ 90%
- [ ] Zero regressions

**Documentation:**
- [ ] All planning docs complete
- [ ] All code documented
- [ ] CHANGELOG updated
- [ ] README updated (if needed)

### 13.2 Quality Gates

**Must Pass:**
- [ ] `pytest tests/ -v` → Exit code 0
- [ ] `mypy src/code_forge/` → Exit code 0
- [ ] `ruff check src/code_forge/` → Exit code 0
- [ ] Coverage ≥ 90%
- [ ] All checklist items checked

**Sign-Off:**
- [ ] Self-review complete
- [ ] Peer review complete
- [ ] All feedback addressed
- [ ] Ready to merge

---

## 14. Review Process

### 14.1 Self-Review (Required)

**Before requesting review:**
1. Run all automated checks
2. Review every changed line
3. Check all checklist items
4. Fix all issues found
5. Commit fixes
6. Request peer review

### 14.2 Peer Review (Required)

**Reviewer responsibilities:**
1. Read planning docs
2. Review code changes
3. Run tests locally
4. Check checklist items
5. Provide constructive feedback
6. Approve or request changes

**Review focus areas:**
- Correctness
- Design patterns
- SOLID principles
- Test coverage
- Documentation
- Security
- Performance

### 14.3 Final Review (Required)

**Before merge:**
1. All review feedback addressed
2. All automated checks passing
3. All manual checks complete
4. At least 1 peer approval
5. No outstanding questions
6. Clean commit history

---

## 15. Review Metrics

### 15.1 Code Quality Metrics

**Target Metrics:**
- Cyclomatic complexity: < 10 per function
- Lines of code per file: < 500
- Test coverage: ≥ 90%
- Type coverage: 100%
- Linting violations: 0
- Security issues: 0

**Actual Metrics:**
- [ ] Complexity within limits
- [ ] File sizes reasonable
- [ ] Coverage meets target
- [ ] Types complete
- [ ] Lint clean
- [ ] Security clean

### 15.2 Review Efficiency

**Timeline:**
- Self-review: < 2 hours
- Peer review: < 4 hours
- Address feedback: < 2 hours
- Final review: < 1 hour

**Total:** < 1 day from implementation complete to merge ready

---

## 16. Common Issues Checklist

### 16.1 Prevent Common Mistakes

**Implementation:**
- [ ] Not forgetting to register new agent types
- [ ] Not using wrong agent type names (kebab-case vs snake_case)
- [ ] Not forgetting async/await
- [ ] Not missing type hints
- [ ] Not forgetting docstrings

**Testing:**
- [ ] Not testing implementation details
- [ ] Not forgetting edge cases
- [ ] Not writing flaky tests
- [ ] Not forgetting to mock external dependencies
- [ ] Not leaving debug code

**Documentation:**
- [ ] Not forgetting to update CHANGELOG
- [ ] Not leaving TODOs
- [ ] Not copying outdated examples
- [ ] Not using confusing terminology

---

## 17. Reviewer Feedback Template

```markdown
## Review of Specialized Agents Phase

### Summary
[Overall assessment]

### Strengths
- [What was done well]
- [Good design decisions]
- [Quality highlights]

### Issues Found

#### Critical (Must Fix)
- [ ] [Issue description]
- [ ] [Another issue]

#### Major (Should Fix)
- [ ] [Issue description]

#### Minor (Nice to Have)
- [ ] [Suggestion]

### Questions
- [Clarification needed]
- [Design decision rationale]

### Recommendation
- [ ] Approve
- [ ] Approve with minor changes
- [ ] Request changes
- [ ] Reject

**Reviewer:** _________
**Date:** _________
```

---

## 18. Approval Criteria

### 18.1 Merge Approval Required When

**All of:**
- [ ] All automated checks pass
- [ ] All manual checklist items checked
- [ ] At least 1 peer approval
- [ ] All critical and major issues resolved
- [ ] Author confirms ready to merge
- [ ] No outstanding questions

### 18.2 Final Sign-Off

**Implementation Complete:**
- **Author:** _________________ Date: _________
- **Peer Reviewer:** _________________ Date: _________
- **Final Reviewer:** _________________ Date: _________

**Quality Gates Passed:**
- [ ] Code quality
- [ ] Test coverage
- [ ] Documentation
- [ ] Security
- [ ] Performance
- [ ] Backward compatibility

**Phase Status:** ⬜ In Review ⬜ Approved ⬜ Merged

---

## 19. Post-Merge Review

### 19.1 After Merge Checklist

- [ ] All tests still passing in main
- [ ] No integration issues
- [ ] Documentation deployed
- [ ] Version tagged
- [ ] Stakeholders notified
- [ ] Monitoring for issues

### 19.2 Retrospective

**What Went Well:**
- [Positive aspects]

**What Could Be Improved:**
- [Areas for improvement]

**Action Items:**
- [Concrete next steps]

---

This completes the code review checklist. Use this document to ensure consistent, high-quality code reviews throughout the implementation phase.
