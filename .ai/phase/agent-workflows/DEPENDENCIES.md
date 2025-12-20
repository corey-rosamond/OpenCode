# Agent Workflow System: Dependencies

**Phase:** agent-workflows
**Version Target:** 1.7.0
**Created:** 2025-12-21

This document outlines all dependencies and integration points for the workflow system.

---

## Hard Dependencies (Must Exist)

### 1. Agent System (v1.6.0) - CRITICAL

**Required Components:**
- `src/code_forge/agents/base.py`
  - `Agent` - Base class for all agents
  - `AgentConfig` - Configuration for agent creation
  - `AgentState` - Agent state tracking
  - `ResourceLimits` - Resource limit enforcement

- `src/code_forge/agents/types.py`
  - `AgentTypeDefinition` - Agent type metadata
  - `AgentTypeRegistry` - Registry of all 20 agent types

- `src/code_forge/agents/manager.py`
  - `AgentManager` - Agent lifecycle management
  - Spawning agents
  - Collecting agent results

- `src/code_forge/agents/result.py`
  - `AgentResult` - Structured agent results

**Why Critical:**
Workflows orchestrate agents. Without the agent system, workflows have nothing to execute.

**Integration Points:**
- WorkflowExecutor uses AgentManager to spawn agents
- StepExecutor collects AgentResult from each step
- Workflow validation checks agent types exist in AgentTypeRegistry
- Step resource limits inherit from agent resource limits

**Version Required:** v1.6.0 or later

---

### 2. Session System - CRITICAL

**Required Components:**
- `src/code_forge/sessions/storage.py`
  - `SessionStorage` - JSON file persistence
  - `save()`, `load()` methods

- `src/code_forge/sessions/models.py`
  - `Session` - Session data model
  - `SessionMessage` - Message format

- `src/code_forge/sessions/manager.py`
  - `SessionManager` - Session lifecycle

**Why Critical:**
Workflow state must be persisted to enable resumability. Sessions provide the persistence layer.

**Integration Points:**
- WorkflowState saved to session storage
- Checkpoints stored as session data
- Workflow messages in session history
- Resume from session workflow states

**Storage Location:**
- Workflow states: `.forge/workflows/states/workflow_{id}.json`
- Checkpoints: `.forge/workflows/checkpoints/{workflow_id}/step_{id}.json`

---

### 3. Tool System - CRITICAL

**Required Components:**
- `src/code_forge/tools/base.py`
  - `BaseTool` - Base class for tools
  - `ToolParameter` - Parameter definition
  - `ToolResult` - Tool execution result
  - `ExecutionContext` - Execution context

- `src/code_forge/tools/registry.py`
  - `ToolRegistry` - Singleton tool registry

**Why Critical:**
WorkflowTool must integrate with the tool system to be accessible to agents and LLM.

**Integration Points:**
- WorkflowTool extends BaseTool
- WorkflowTool registered in ToolRegistry
- Workflow execution available as a tool call

---

### 4. Permission System - CRITICAL

**Required Components:**
- `src/code_forge/permissions/checker.py`
  - `PermissionChecker` - Permission validation

- `src/code_forge/permissions/models.py`
  - `PermissionLevel` - ALLOW, DENY, ASK
  - `PermissionRule` - Rule definition

**Why Critical:**
Workflow execution must be gated by permissions for security.

**Integration Points:**
- Workflow execution requires permission check
- Individual agent executions still check permissions
- WorkflowTool respects permission system

**Required Permissions:**
```python
PermissionRule(
    name="workflow_execution",
    pattern="tool:workflow:*",
    level=PermissionLevel.ASK,
    description="Execute multi-agent workflows",
)
```

---

### 5. Command System - CRITICAL

**Required Components:**
- `src/code_forge/commands/base.py`
  - `Command` - Base class for commands
  - `CommandResult` - Command execution result

- `src/code_forge/commands/registry.py`
  - `CommandRegistry` - Singleton command registry

- `src/code_forge/commands/executor.py`
  - `CommandExecutor` - Command execution

**Why Critical:**
Workflow commands must integrate with the existing command infrastructure.

**Integration Points:**
- WorkflowCommand extends Command
- WorkflowCommand registered in CommandRegistry
- `/workflow` commands available in REPL

---

### 6. Core Infrastructure - CRITICAL

**Required Components:**
- `src/code_forge/core/errors.py`
  - `CodeForgeError` - Base exception class
  - Custom exception hierarchy

- `src/code_forge/core/logging.py`
  - `get_logger()` - Logger factory

- `src/code_forge/core/types.py`
  - Core type definitions

**Why Critical:**
Foundational infrastructure for error handling and logging.

**Integration Points:**
- WorkflowError extends CodeForgeError
- All workflow components use get_logger()
- Type definitions for workflow models

---

## Soft Dependencies (Optional But Useful)

### 7. Hook System - OPTIONAL

**Required Components:**
- `src/code_forge/hooks/executor.py`
  - `fire_event()` - Fire lifecycle hooks

- `src/code_forge/hooks/events.py`
  - `EventType` - Event type enumeration

**Why Useful:**
Enables lifecycle event handling for workflows.

**Integration Points:**
- Fire `workflow:pre_execute` before workflow starts
- Fire `workflow:post_execute` after workflow completes
- Fire `workflow:step_complete` after each step
- Fire `workflow:failed` on workflow failure

**If Missing:**
Workflow system works but without lifecycle hooks. No critical functionality lost.

---

### 8. Context System - OPTIONAL

**Required Components:**
- `src/code_forge/context/tokens.py`
  - `TokenCounter` - Token counting

**Why Useful:**
Track token usage across workflow execution.

**Integration Points:**
- Count tokens used by all workflow steps
- Report total workflow token usage

**If Missing:**
Workflow system works but without token tracking. Agents still enforce their own limits.

---

### 9. Web Tools - OPTIONAL

**Required Components:**
- `src/code_forge/web/tools.py`
  - `WebSearchTool`
  - `WebFetchTool`

**Why Useful:**
Some workflow templates use web tools (research agent).

**Integration Points:**
- Research agent in workflows uses web tools
- Optional dependency for specific agent types

**If Missing:**
Workflows not using web tools still work. Templates requiring web tools fail gracefully.

---

## External Dependencies (Python Packages)

### Required Packages

```toml
[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"        # Model validation
pyyaml = "^6.0"          # YAML parsing
asyncio = "*"            # Async execution (stdlib)
dataclasses = "*"        # Data models (stdlib)
typing = "*"             # Type hints (stdlib)
pathlib = "*"            # File paths (stdlib)
json = "*"               # JSON serialization (stdlib)
datetime = "*"           # Timestamps (stdlib)
```

### Optional Packages

```toml
[tool.poetry.dev-dependencies]
pytest = "^7.0"          # Testing
pytest-asyncio = "^0.21" # Async test support
pytest-cov = "^4.0"      # Coverage reporting
mypy = "^1.0"            # Type checking
ruff = "^0.1"            # Linting
```

**All required packages already exist in Code-Forge dependencies.**

---

## Integration Points Summary

### Inbound Dependencies (What Workflow Needs)

| Component | Required For | Critical? |
|-----------|-------------|-----------|
| AgentManager | Spawning agents | Yes |
| AgentTypeRegistry | Validating agent types | Yes |
| AgentResult | Collecting step results | Yes |
| SessionStorage | Persisting state | Yes |
| ToolRegistry | Registering WorkflowTool | Yes |
| PermissionChecker | Security | Yes |
| CommandRegistry | Slash commands | Yes |
| HookExecutor | Lifecycle events | No |
| TokenCounter | Usage tracking | No |

### Outbound Dependencies (What Depends on Workflow)

**Currently:** None

**Future:**
- CLI/REPL may display workflow progress
- Agent system may spawn sub-workflows (future enhancement)
- Plugins may register custom workflow templates

---

## Version Dependencies

### Minimum Required Versions

- **Python:** 3.10+
- **Code-Forge:** v1.6.0+ (for 20 agent types)
- **Pydantic:** v2.0+
- **PyYAML:** v6.0+

### Breaking Changes to Monitor

**Agent System Changes:**
- If `AgentManager` API changes, WorkflowExecutor must adapt
- If `AgentResult` structure changes, StepResult must adapt
- If agent type registration changes, validation must adapt

**Session System Changes:**
- If `SessionStorage` API changes, StateManager must adapt
- If storage format changes, migration required

**Tool System Changes:**
- If `BaseTool` interface changes, WorkflowTool must adapt

**Command System Changes:**
- If `Command` interface changes, WorkflowCommand must adapt

---

## Pre-Implementation Checklist

Before implementation begins, verify:

- [ ] v1.6.0 is complete and merged
- [ ] All 20 agent types exist and work
- [ ] AgentManager can spawn agents
- [ ] SessionStorage works correctly
- [ ] ToolRegistry accepts tool registration
- [ ] PermissionChecker enforces rules
- [ ] CommandRegistry accepts command registration
- [ ] All existing tests pass

**Verification Command:**
```bash
pytest tests/ -v
python -c "from code_forge.agents.types import AgentTypeRegistry; assert len(AgentTypeRegistry().list_types()) == 20"
```

---

## Implementation Order Based on Dependencies

### Phase 1: No External Dependencies
- Core models (WorkflowDefinition, WorkflowStep, etc.)
- Graph construction and validation
- Condition expression parser and evaluator

**Why First:** These components are self-contained.

### Phase 2: Session System Dependency
- State management
- Checkpoint creation and restoration

**Why Second:** Requires SessionStorage to be working.

### Phase 3: Agent System Dependency
- Workflow executor
- Step executor
- Parallel executor

**Why Third:** Requires AgentManager to spawn agents.

### Phase 4: Tool & Command System Dependencies
- WorkflowTool
- WorkflowCommand
- Template registry

**Why Fourth:** Requires ToolRegistry and CommandRegistry.

### Phase 5: All Systems Integration
- Hook integration
- Permission integration
- Session integration
- End-to-end testing

**Why Last:** Requires all other systems to be working.

---

## Risk Assessment

### High Risk Dependencies

**Agent System (AgentManager, AgentResult):**
- **Risk:** Core to workflow execution
- **Mitigation:** Comprehensive interface testing, mock agents in unit tests
- **Fallback:** None - workflow system cannot work without agents

**Session System (SessionStorage):**
- **Risk:** Required for state persistence
- **Mitigation:** Abstract storage interface, comprehensive storage tests
- **Fallback:** In-memory state only (no resume capability)

### Medium Risk Dependencies

**Permission System:**
- **Risk:** Security requirement
- **Mitigation:** Default to ASK if permission system fails
- **Fallback:** Prompt user for all workflows

**Command System:**
- **Risk:** Primary user interface
- **Mitigation:** WorkflowTool provides alternative access
- **Fallback:** LLM can execute workflows via tool

### Low Risk Dependencies

**Hook System:**
- **Risk:** Optional feature
- **Mitigation:** Graceful degradation if hooks not available
- **Fallback:** Workflows work without hooks

**Context System:**
- **Risk:** Optional token tracking
- **Mitigation:** Agent limits still enforced
- **Fallback:** No workflow-level token tracking

---

## Testing Dependencies

### Test Infrastructure Required

- **pytest** - Test runner
- **pytest-asyncio** - Async test support
- **unittest.mock** - Mocking framework
- **pytest-cov** - Coverage reporting

### Mock Requirements

For unit tests, must be able to mock:
- [ ] AgentManager (spawn agents, collect results)
- [ ] AgentTypeRegistry (validate agent types)
- [ ] SessionStorage (save/load state)
- [ ] PermissionChecker (permission checks)
- [ ] HookExecutor (fire events)

**Mock Strategies:**
- Use unittest.mock.AsyncMock for async methods
- Create fixture factories for common mocks
- Shared conftest.py with workflow mocks

---

## Documentation Dependencies

### Required Documentation

- [ ] Agent system docs (how agents work)
- [ ] Session system docs (state persistence)
- [ ] Permission system docs (security model)
- [ ] Command system docs (slash commands)

### Documentation to Create

- [ ] Workflow system user guide
- [ ] Workflow template creation guide
- [ ] Python API reference
- [ ] YAML schema reference
- [ ] Troubleshooting guide

---

## Migration Considerations

**No migration required** because:
- Workflow system is new functionality
- No existing data to migrate
- No breaking changes to existing systems
- Purely additive feature

**Future migration scenarios:**
1. If workflow YAML schema changes → migration tool needed
2. If state storage format changes → backward compatibility layer
3. If agent interface changes → workflow executor adaptation

---

## Compatibility Matrix

| Code-Forge Version | Workflow Support | Notes |
|--------------------|-----------------|-------|
| < 1.6.0 | ❌ No | Missing specialized agents |
| 1.6.0 | ⚠️ Partial | Agents exist, no workflow system |
| 1.7.0 | ✅ Yes | Full workflow support |
| 1.8.0+ | ✅ Yes | Enhanced workflow features |

---

## Dependency Diagram

```
┌─────────────────────────────────────────┐
│         Workflow System (v1.7.0)        │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
    ┌─────┐    ┌─────┐    ┌─────┐
    │Agent│    │Sess │    │Tool │
    │ Sys │    │ Sys │    │ Sys │
    │1.6.0│    │     │    │     │
    └─────┘    └─────┘    └─────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
            ┌───────────────┐
            │  Core System  │
            │(errors, logs) │
            └───────────────┘
```

**Optional Dependencies:**
```
Workflow System
    ├── Hook System (optional)
    ├── Context System (optional)
    └── Web Tools (optional)
```

---

## Summary

**Critical Dependencies (Must Have):**
1. Agent System v1.6.0
2. Session System
3. Tool System
4. Permission System
5. Command System
6. Core Infrastructure

**Optional Dependencies (Nice to Have):**
1. Hook System
2. Context System
3. Web Tools

**External Dependencies:**
All required Python packages already in Code-Forge.

**Risk Level:** Low to Medium
- Agent system is stable (v1.6.0)
- Session system is mature
- Clear integration points
- Comprehensive testing planned

**Ready to Proceed:** ✅ Yes
All critical dependencies exist and are stable.
