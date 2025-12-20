# Specialized Task Agents: Dependencies

**Phase:** specialized-agents
**Version Target:** 1.6.0
**Created:** 2025-12-21

Documents all dependencies, integration points, and system interactions.

---

## 1. Internal Dependencies

### 1.1 Core Module Dependencies

| Module | Usage | Files Affected |
|--------|-------|----------------|
| `agents/base.py` | Base classes for all agents | All 16 new agent files |
| `agents/types.py` | Agent type definitions and registry | types.py (modified) |
| `agents/result.py` | AgentResult for execution outcomes | All agent implementations |
| `agents/executor.py` | Agent execution engine | Integration with new agents |
| `agents/manager.py` | Agent lifecycle management | Spawn/manage new agent types |

**Integration Points:**
- All new agents **must inherit** from `Agent` base class
- All new agents **must be registered** in `AgentTypeRegistry`
- All new agents **must return** `AgentResult` from `execute()`

### 1.2 Tool System Dependencies

| Module | Usage | Agents Affected |
|--------|-------|-----------------|
| `tools/base.py` | Tool execution | All agents |
| `tools/registry.py` | Tool availability lookup | All agents |
| `tools/file/` | File operations | Most agents |
| `tools/execution/bash.py` | Command execution | debug, qa-manual, log-analysis, performance-analysis, security-audit, dependency-analysis, migration-planning |
| `web/tools.py` | Web search/fetch | writing, research, tutorial, dependency-analysis |
| `git/` | Git operations | communication |
| `github/` | GitHub API | communication |

**Tool Access Matrix:**

```
Tool           | Coding | Writing | Visual | QA | Research | Security | Project
---------------|--------|---------|--------|----|-----------|---------|---------
glob           |   ●●●● |    ○○●  |   ●    | ○  |    ○      |   ●●    |   ●●
grep           |   ●●●● |    ○○●  |   ●    | ○  |   ○●●     |   ●●    |   ●●
read           |   ●●●● |   ●●●   |   ●    | ●  |   ●●●     |   ●●    |   ●●
write          |   ●●●● |   ●●●   |   ●    | ●  |   ●●●     |   ●●    |   ●●
edit           |    ○○●○ |    ○○○  |   ○    | ○  |    ○      |   ○○    |   ○●
bash           |    ○○○● |    ○○○  |   ○    | ●  |   ○●●     |   ●●    |   ○●
web-search     |    ○○○○ |   ●○●   |   ○    | ○  |   ●○○     |   ○●    |   ○○
web-fetch      |    ○○○○ |   ●○○   |   ○    | ○  |   ●○○     |   ○○    |   ○○
git            |    ○○○○ |   ○●○   |   ○    | ○  |    ○      |   ○○    |   ○○
github         |    ○○○○ |   ○●○   |   ○    | ○  |    ○      |   ○○    |   ○○

Legend: ● = Required, ○ = Not available
Coding: test-generation, documentation, refactoring, debug
Writing: writing, communication, tutorial
Visual: diagram
QA: qa-manual
Research: research, log-analysis, performance-analysis
Security: security-audit, dependency-analysis
Project: migration-planning, configuration
```

**Integration Constraints:**
- Agents can ONLY use tools in their `default_tools` list
- Tool restrictions enforced by `ToolExecutor`
- Attempting restricted tools must raise clear error

### 1.3 LangChain Integration

| Module | Usage | Integration Point |
|--------|-------|-------------------|
| `langchain/agent.py` | CodeForgeAgent execution | Agents may use internally |
| `langchain/llm.py` | LLM calls | All agents use for reasoning |
| `langchain/memory.py` | Conversation memory | Context for agents |
| `langchain/callbacks.py` | Execution callbacks | Streaming, logging |
| `langchain/prompts.py` | Prompt generation | System prompts for agents |

**Critical Integration:**
- Each agent type has specialized system prompt in `prompt_template`
- Prompts inject domain-specific guidance
- LLM calls respect agent resource limits

### 1.4 Permission System Dependencies

| Module | Usage | Integration |
|--------|-------|-------------|
| `permissions/checker.py` | Permission validation | All tool calls |
| `permissions/rules.py` | Rule matching | Tool restrictions |
| `permissions/prompt.py` | User confirmation | Restricted operations |

**Permission Flow:**
1. Agent requests tool execution
2. PermissionChecker validates against rules
3. If denied, user prompted (if interactive)
4. Agent receives allow/deny decision

### 1.5 Hook System Dependencies

| Module | Usage | Events Fired |
|--------|-------|--------------|
| `hooks/executor.py` | Event firing | tool.before_execute, tool.after_execute |
| `hooks/events.py` | Event types | HookEvent instances |
| `hooks/registry.py` | Hook lookup | Configured hooks |

**Hook Events:**
- `agent.before_execute` - Before agent starts
- `agent.after_execute` - After agent completes
- `tool.before_execute` - Before each tool call
- `tool.after_execute` - After each tool call

### 1.6 Session System Dependencies

| Module | Usage | Integration |
|--------|-------|-------------|
| `sessions/manager.py` | Session persistence | Agent messages/results |
| `sessions/storage.py` | Session storage | Agent execution history |
| `sessions/models.py` | Session data models | Message, ToolInvocation |

**Session Integration:**
- Agent messages added to session history
- Agent results stored in session
- Session persisted across executions

### 1.7 Context Management Dependencies

| Module | Usage | Integration |
|--------|-------|-------------|
| `context/manager.py` | Context limits | Agent execution |
| `context/tokens.py` | Token counting | Resource tracking |
| `context/limits.py` | Context budgets | Agent limits |

**Resource Tracking:**
- Token usage tracked per agent
- Context limits enforced
- Budget warnings when approaching limits

---

## 2. External Dependencies

### 2.1 Python Standard Library

| Module | Usage | Agents |
|--------|-------|--------|
| `asyncio` | Async execution | All agents |
| `threading` | Thread safety | Registry |
| `abc` | Abstract base classes | Agent base |
| `dataclasses` | Data structures | Config, Result |
| `datetime` | Timestamps | All agents |
| `uuid` | Agent IDs | All agents |
| `logging` | Logging | All agents |
| `typing` | Type hints | All agents |
| `enum` | State enums | Agent state |

**No new external dependencies required** - all agents use existing stdlib modules.

### 2.2 Third-Party Dependencies (Existing)

| Package | Usage | Agents |
|---------|-------|--------|
| `langchain` | LLM orchestration | All agents |
| `aiohttp` | Async HTTP | research, writing, tutorial, dependency-analysis |
| `pytest` | Testing framework | Test suite |
| `mypy` | Type checking | Development |
| `ruff` | Linting | Development |

**No new third-party dependencies** - uses existing project dependencies.

### 2.3 External Services

| Service | Usage | Agents |
|---------|-------|--------|
| OpenRouter API | LLM calls | All agents |
| Web search providers | Research | research, writing, tutorial, dependency-analysis |
| GitHub API | Repository info | communication |

**Service Availability:**
- Agents fail gracefully if services unavailable
- Clear error messages for service failures
- No hard dependencies on external services for core functionality

---

## 3. File System Dependencies

### 3.1 Required Files

**New Files Created:**
```
src/code_forge/agents/builtin/
├── test_generation.py
├── documentation.py
├── refactoring.py
├── debug.py
├── writing.py
├── communication.py
├── tutorial.py
├── diagram.py
├── qa_manual.py
├── research.py
├── log_analysis.py
├── performance_analysis.py
├── security_audit.py
├── dependency_analysis.py
├── migration_planning.py
└── configuration.py
```

**Modified Files:**
```
src/code_forge/agents/
├── types.py              # Add 16 new AgentTypeDefinitions
└── builtin/__init__.py   # Export 16 new agent classes
```

**No deletions** - purely additive changes.

### 3.2 Test Files Created

```
tests/unit/agents/builtin/
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

tests/integration/
└── test_all_specialized_agents.py
```

---

## 4. Configuration Dependencies

### 4.1 No Configuration Changes Required

- Agent types registered programmatically
- No YAML/TOML config files needed
- No environment variables required
- No user config changes

### 4.2 Optional Configuration

Users **may** configure:
- Per-agent resource limits (via AgentConfig overrides)
- Tool permissions (via ~/.forge/permissions.yaml)
- Hooks for agent events (via ~/.forge/hooks.yaml)

But defaults work out of the box.

---

## 5. Backward Compatibility

### 5.1 No Breaking Changes

| Component | Change Type | Impact |
|-----------|-------------|--------|
| Agent base classes | None | No impact |
| AgentConfig | None | No impact |
| AgentTypeRegistry API | Additive only | No breaking changes |
| Existing agent types | Unchanged | No impact |
| Tool system | None | No impact |
| Permission system | None | No impact |

### 5.2 API Compatibility

**Guaranteed Compatible:**
- All existing `AgentConfig.for_type()` calls work
- All existing agent instantiation works
- All existing tool restrictions work
- All existing tests pass

**New Capabilities:**
- 16 new agent types available
- No changes to existing APIs required

---

## 6. Integration Risks

### 6.1 Tool Restriction Enforcement

**Risk:** Agent uses tool not in `default_tools`
**Mitigation:**
- ToolExecutor validates tool access
- Clear error messages for denied tools
- Tests verify tool restrictions

**Dependency:** `tools/executor.py` must enforce restrictions

### 6.2 Resource Limit Enforcement

**Risk:** Agent exceeds token/time limits
**Mitigation:**
- Context manager tracks usage
- Execution terminated at limits
- Clear error messages

**Dependency:** `context/manager.py` must track and enforce limits

### 6.3 Concurrent Agent Execution

**Risk:** Race conditions between agents
**Mitigation:**
- Singleton registries use RLock
- Agents are independent
- No shared mutable state

**Dependency:** Thread safety in `types.py:AgentTypeRegistry`

### 6.4 Prompt Quality

**Risk:** Poor prompts = ineffective agents
**Mitigation:**
- Thorough prompt engineering
- Testing with real scenarios
- Iterative refinement

**Dependency:** Quality of `prompt_template` in each AgentTypeDefinition

---

## 7. Inter-Module Dependencies

### 7.1 Dependency Graph

```
agents/types.py
    ↓
agents/builtin/*.py
    ↓ (inherits from)
agents/base.py
    ↓ (uses)
agents/result.py
    ↓ (returns)
agents/executor.py
    ↓ (integrates with)
├── tools/
├── permissions/
├── hooks/
├── sessions/
├── context/
└── langchain/
```

### 7.2 Critical Paths

**Agent Execution Flow:**
1. User requests agent → `agents/manager.py`
2. Create config → `agents/types.py:AgentConfig.for_type()`
3. Instantiate agent → `agents/builtin/{type}.py`
4. Execute → `agents/executor.py`
5. Tools → `tools/executor.py`
6. Permissions → `permissions/checker.py`
7. Hooks → `hooks/executor.py`
8. LLM calls → `langchain/llm.py`
9. Result → `agents/result.py`
10. Persist → `sessions/storage.py`

**All modules in this path are critical dependencies.**

---

## 8. Testing Dependencies

### 8.1 Test Framework Dependencies

| Dependency | Usage |
|------------|-------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `pytest-mock` | Mocking |
| `pytest-cov` | Coverage reporting |

### 8.2 Test Fixtures

Tests depend on:
- Mock LLM responses
- Mock tool execution
- Mock file system
- Mock external services

All fixtures in `tests/conftest.py`.

---

## 9. Development Dependencies

### 9.1 Required for Development

| Tool | Purpose |
|------|---------|
| `mypy` | Type checking |
| `ruff` | Linting |
| `black` | Code formatting (optional) |
| `pytest` | Testing |

### 9.2 Optional Development Tools

- `ipdb` - Debugging
- `pytest-watch` - Continuous testing
- `coverage` - Coverage reports

---

## 10. Deployment Dependencies

### 10.1 No Additional Deployment Dependencies

- No new packages to install
- No new services to configure
- No new infrastructure required

### 10.2 Version Requirements

- Python ≥ 3.10 (existing requirement)
- All existing dependencies at current versions
- No version bumps required

---

## 11. Documentation Dependencies

### 11.1 Planning Documents

This phase depends on:
- [x] PLAN.md - Implementation strategy
- [x] GHERKIN.md - Behavior specifications
- [x] COMPLETION_CRITERIA.md - Acceptance criteria
- [x] DEPENDENCIES.md - This document
- [ ] TESTS.md - Test strategy
- [ ] REVIEW.md - Review checklist

### 11.2 Code Documentation

Depends on:
- Docstring conventions (Google style)
- Type hint conventions (PEP 484)
- Comment conventions (clear, concise)

---

## 12. Dependency Resolution

### 12.1 Circular Dependencies

**None identified** - clean dependency graph.

### 12.2 Missing Dependencies

**None** - all required modules exist.

### 12.3 Version Conflicts

**None** - no conflicting version requirements.

---

## 13. Integration Testing Dependencies

### 13.1 Integration Points to Test

- [ ] Agent ↔ Tool system
- [ ] Agent ↔ Permission system
- [ ] Agent ↔ Hook system
- [ ] Agent ↔ Session system
- [ ] Agent ↔ Context manager
- [ ] Agent ↔ LangChain
- [ ] Multi-agent concurrent execution

### 13.2 Test Dependencies

Tests require:
- Mock implementations of all integration points
- Async test support
- Concurrent execution test utilities

All available in existing test infrastructure.

---

## 14. Future Dependencies

### 14.1 Potential Future Needs

If implementing FEAT-003 (Agent Workflows):
- Workflow orchestration system
- Agent coordination mechanism
- Shared context management
- Dependency graph resolution

**Not needed for this phase.**

### 14.2 Extension Points

Future extensions might depend on:
- Plugin system for custom agent types
- Agent marketplace
- Agent performance analytics
- Agent learning/improvement system

**All designed to be additive, non-breaking.**

---

## 15. Summary

### 15.1 Critical Dependencies

1. `agents/base.py` - Base Agent class
2. `agents/types.py` - AgentTypeRegistry
3. `agents/result.py` - AgentResult
4. `tools/executor.py` - Tool execution
5. `langchain/llm.py` - LLM calls

### 15.2 No New External Dependencies

This phase requires **zero new external packages**.

### 15.3 Integration Status

| System | Dependency Type | Status |
|--------|----------------|--------|
| Tool System | Required | ✅ Exists |
| Permission System | Required | ✅ Exists |
| Hook System | Required | ✅ Exists |
| Session System | Required | ✅ Exists |
| Context Manager | Required | ✅ Exists |
| LangChain | Required | ✅ Exists |

**All required dependencies exist and are stable.**

---

## 16. Dependency Checklist

Before implementation:
- [x] All internal dependencies identified
- [x] All external dependencies identified
- [x] Integration points documented
- [x] No circular dependencies
- [x] No missing dependencies
- [x] No version conflicts
- [x] Backward compatibility ensured
- [x] Test dependencies available

**Ready for implementation: Yes**
