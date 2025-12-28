# FEAT-002: Multi-Agent Tools & Web Search Integration - Implementation Plan

**Phase:** llm-tool-integration
**Version Target:** 1.10.0
**Created:** 2025-12-28
**Status:** Planning

---

## Overview

Two critical features are missing that prevent the LLM from accessing core Code-Forge capabilities:

1. **TaskTool**: LLM cannot spawn sub-agents (infrastructure exists but no tool exposed)
2. **Web Search/Fetch**: Exists in web module but isn't registered as BaseTool

Additionally, agents should have access to RAG for context-aware responses.

### Problem Statement

The agent infrastructure (20+ specialized agents) is complete but inaccessible to the LLM because no `TaskTool` exists. Web search/fetch functionality exists but isn't in the tool registry.

---

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | TaskTool allows LLM to spawn any registered agent type | Must Have |
| FR-2 | TaskTool passes RAG context to spawned agents | Must Have |
| FR-3 | WebSearchBaseTool wraps existing web search as BaseTool | Must Have |
| FR-4 | WebFetchBaseTool wraps existing web fetch as BaseTool | Must Have |
| FR-5 | All tools registered in ToolRegistry and visible to LLM | Must Have |
| NFR-1 | Test coverage > 90% | Must Have |
| NFR-2 | No breaking changes to existing tools | Must Have |

---

## Part 1: TaskTool Implementation

### Files to Create

```
src/code_forge/tools/task/
    __init__.py          # Module init with register_task_tools()
    task.py              # TaskTool implementation
```

### TaskTool Design

**Key Features:**
- Spawn sub-agents (explore, plan, code-review, etc.)
- Pass RAG manager to spawned agents for context
- Support wait/background execution modes
- Inherit conversation context option

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_type | string | Yes | Type: explore, plan, code-review, general, etc. |
| task | string | Yes | Task description for agent |
| wait | boolean | No | Wait for completion (default: true) |
| inherit_context | boolean | No | Share parent conversation |
| use_rag | boolean | No | Enable RAG for agent (default: true) |

**RAG Integration:**
- TaskTool receives RAGManager via ExecutionContext metadata
- Passes RAGManager to spawned agent's context
- Agent can query RAG for relevant code context

### Implementation Approach

```python
# src/code_forge/tools/task/task.py
class TaskTool(BaseTool):
    @property
    def name(self) -> str:
        return "Task"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TASK

    async def _execute(self, context: ExecutionContext, **kwargs) -> ToolResult:
        agent_type = kwargs["agent_type"]
        task = kwargs["task"]
        use_rag = kwargs.get("use_rag", True)

        # Get RAG manager from context if available
        rag_manager = context.metadata.get("rag_manager")

        # Build agent context with RAG
        agent_context = AgentContext(
            working_directory=context.working_dir,
            rag_manager=rag_manager if use_rag else None,
        )

        # Spawn agent via AgentManager
        manager = AgentManager.get_instance()
        agent = await manager.spawn(agent_type, task, context=agent_context)

        return ToolResult.ok(agent.result.output)
```

---

## Part 2: Web Tools Conversion

### Files to Create

```
src/code_forge/tools/web/
    __init__.py          # Module init with register_web_tools()
    search.py            # WebSearchBaseTool (BaseTool subclass)
    fetch.py             # WebFetchBaseTool (BaseTool subclass)
```

### WebSearchBaseTool Design

**Converts existing `src/code_forge/web/tools.py:WebSearchTool` to BaseTool pattern.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query |
| num_results | integer | No | Results count (default: 10) |
| provider | string | No | duckduckgo, brave, google |
| allowed_domains | array | No | Domain whitelist |
| blocked_domains | array | No | Domain blacklist |

### WebFetchBaseTool Design

**Converts existing `src/code_forge/web/tools.py:WebFetchTool` to BaseTool pattern.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | string | Yes | URL to fetch |
| format | string | No | markdown, text, raw |
| use_cache | boolean | No | Use cache (default: true) |
| timeout | integer | No | Timeout seconds |

---

## Part 3: Update Tool Registration

### File to Modify

`src/code_forge/tools/__init__.py`

### Changes

```python
# Add imports
from code_forge.tools.task import register_task_tools
from code_forge.tools.web import register_web_tools

def register_all_tools() -> None:
    """Register all built-in tools with the registry."""
    register_file_tools()
    register_execution_tools()
    register_task_tools()      # NEW
    register_web_tools()       # NEW
```

---

## Part 4: RAG Integration for Agents

### File to Modify

`src/code_forge/cli/dependencies.py`

### Changes

Pass RAGManager to tool execution context so TaskTool can access it:

```python
# In Dependencies.create() or where tools are executed
# Ensure rag_manager is added to ExecutionContext metadata
context = ExecutionContext(
    working_dir=str(Path.cwd()),
    metadata={"rag_manager": rag_manager},
)
```

### Agent Context Enhancement

Ensure `AgentContext` (in `src/code_forge/agents/base.py`) includes RAGManager:

```python
@dataclass
class AgentContext:
    working_directory: str
    rag_manager: RAGManager | None = None
    # ... existing fields
```

---

## Part 5: Test Coverage

### New Test Files

```
tests/unit/tools/task/
    __init__.py
    test_task.py         # TaskTool tests

tests/unit/tools/web/
    __init__.py
    test_search.py       # WebSearchBaseTool tests
    test_fetch.py        # WebFetchBaseTool tests
```

### Key Test Cases

**TaskTool:**
- Test spawning each agent type
- Test unknown agent type error
- Test wait vs background mode
- Test RAG context passing
- Test inherit_context option

**WebSearchBaseTool:**
- Test search execution
- Test domain filtering
- Test provider selection
- Test no results handling

**WebFetchBaseTool:**
- Test URL fetching
- Test format conversion
- Test cache behavior
- Test error handling

---

## Critical Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/code_forge/tools/task/__init__.py` | Create | Task tools module |
| `src/code_forge/tools/task/task.py` | Create | TaskTool implementation |
| `src/code_forge/tools/web/__init__.py` | Create | Web tools module |
| `src/code_forge/tools/web/search.py` | Create | WebSearchBaseTool |
| `src/code_forge/tools/web/fetch.py` | Create | WebFetchBaseTool |
| `src/code_forge/tools/__init__.py` | Modify | Add registration calls |
| `src/code_forge/cli/dependencies.py` | Modify | Pass RAG to context |
| `src/code_forge/agents/base.py` | Modify | Add rag_manager to AgentContext |

---

## Existing Code References

- BaseTool pattern: `src/code_forge/tools/base.py:202-488`
- Tool registration: `src/code_forge/tools/file/__init__.py:22-31`
- Agent types: `src/code_forge/agents/types.py:14-828`
- AgentManager: `src/code_forge/agents/manager.py`
- Web search impl: `src/code_forge/web/search/`
- Web fetch impl: `src/code_forge/web/fetch/`
- RAG manager: `src/code_forge/rag/manager.py`

---

## Success Criteria

1. TaskTool registered and visible to LLM
2. TaskTool can spawn any of 20+ agent types
3. WebSearchBaseTool registered and visible to LLM
4. WebFetchBaseTool registered and visible to LLM
5. RAGManager passed to spawned agents
6. All tests pass (90%+ coverage)
7. No regressions in existing functionality

---

## Implementation Order

### Step 1: TaskTool
- Create `src/code_forge/tools/task/__init__.py`
- Create `src/code_forge/tools/task/task.py`

### Step 2: Web Tools
- Create `src/code_forge/tools/web/__init__.py`
- Create `src/code_forge/tools/web/search.py`
- Create `src/code_forge/tools/web/fetch.py`

### Step 3: Registration
- Modify `src/code_forge/tools/__init__.py`

### Step 4: RAG Integration
- Modify `src/code_forge/agents/base.py` (add rag_manager to AgentContext)
- Modify `src/code_forge/cli/dependencies.py` (pass RAG to context)

### Step 5: Tests
- Create `tests/unit/tools/task/test_task.py`
- Create `tests/unit/tools/web/test_search.py`
- Create `tests/unit/tools/web/test_fetch.py`
