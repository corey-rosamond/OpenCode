# FEAT-002: Multi-Agent Tools & Web Search Integration - Completion Criteria

**Phase:** llm-tool-integration
**Version Target:** 1.10.0

---

## TaskTool Implementation

### TaskTool Core

- [ ] `TaskTool` class inherits from `BaseTool`
- [ ] `name` property returns "Task"
- [ ] `category` property returns `ToolCategory.TASK`
- [ ] `description` property returns clear description
- [ ] `get_parameters()` returns all required parameters
- [ ] `_execute()` spawns agent via AgentManager
- [ ] Handles unknown agent type with clear error
- [ ] Supports `wait` parameter for background execution
- [ ] Supports `use_rag` parameter for RAG context

### TaskTool Registration

- [ ] `register_task_tools()` function exists
- [ ] TaskTool registered with ToolRegistry
- [ ] TaskTool appears in tool list
- [ ] TaskTool accessible to LLM

### TaskTool RAG Integration

- [ ] Receives RAGManager from ExecutionContext
- [ ] Passes RAGManager to spawned agent
- [ ] Agent can use RAG for context

---

## WebSearchBaseTool Implementation

### WebSearchBaseTool Core

- [ ] `WebSearchBaseTool` class inherits from `BaseTool`
- [ ] `name` property returns "WebSearch"
- [ ] `category` property returns `ToolCategory.WEB`
- [ ] `description` property returns clear description
- [ ] `get_parameters()` returns all required parameters
- [ ] `_execute()` calls existing web search implementation
- [ ] Supports `query` parameter (required)
- [ ] Supports `num_results` parameter (optional)
- [ ] Supports `provider` parameter (optional)
- [ ] Supports `allowed_domains` parameter (optional)
- [ ] Supports `blocked_domains` parameter (optional)
- [ ] Formats results appropriately for LLM

### WebSearchBaseTool Registration

- [ ] Part of `register_web_tools()` function
- [ ] Registered with ToolRegistry
- [ ] Appears in tool list
- [ ] Accessible to LLM

---

## WebFetchBaseTool Implementation

### WebFetchBaseTool Core

- [ ] `WebFetchBaseTool` class inherits from `BaseTool`
- [ ] `name` property returns "WebFetch"
- [ ] `category` property returns `ToolCategory.WEB`
- [ ] `description` property returns clear description
- [ ] `get_parameters()` returns all required parameters
- [ ] `_execute()` calls existing web fetch implementation
- [ ] Supports `url` parameter (required)
- [ ] Supports `format` parameter (optional: markdown, text, raw)
- [ ] Supports `use_cache` parameter (optional)
- [ ] Supports `timeout` parameter (optional)
- [ ] Returns content appropriately for LLM

### WebFetchBaseTool Registration

- [ ] Part of `register_web_tools()` function
- [ ] Registered with ToolRegistry
- [ ] Appears in tool list
- [ ] Accessible to LLM

---

## Tool Registration

### Registration Updates

- [ ] `register_task_tools()` added to `register_all_tools()`
- [ ] `register_web_tools()` added to `register_all_tools()`
- [ ] No import errors
- [ ] No registration conflicts
- [ ] All tools appear in registry

---

## RAG Integration

### AgentContext Update

- [ ] `rag_manager` field added to AgentContext
- [ ] Field has proper type hint: `RAGManager | None`
- [ ] Default value is `None`
- [ ] Field documented

### Dependencies Update

- [ ] RAGManager passed in ExecutionContext metadata
- [ ] TaskTool can access RAGManager
- [ ] RAGManager flows to spawned agents

---

## Testing

### TaskTool Tests

- [ ] Test spawning each agent type (at least 5 types)
- [ ] Test unknown agent type returns error
- [ ] Test wait=True waits for completion
- [ ] Test wait=False runs in background
- [ ] Test RAG context is passed to agent
- [ ] Test error handling for agent failures
- [ ] >90% code coverage

### WebSearchBaseTool Tests

- [ ] Test basic search execution
- [ ] Test query parameter validation
- [ ] Test num_results parameter
- [ ] Test provider selection
- [ ] Test domain filtering
- [ ] Test no results handling
- [ ] Test error handling
- [ ] >90% code coverage

### WebFetchBaseTool Tests

- [ ] Test basic URL fetching
- [ ] Test URL validation
- [ ] Test format parameter (markdown, text, raw)
- [ ] Test use_cache parameter
- [ ] Test timeout parameter
- [ ] Test error handling (invalid URL, timeout)
- [ ] >90% code coverage

### Integration Tests

- [ ] Test TaskTool spawns real agent
- [ ] Test WebSearchBaseTool with mock provider
- [ ] Test WebFetchBaseTool with mock response
- [ ] Test all tools in registry after registration

---

## Code Quality

### Verification

- [ ] All files pass `ruff check`
- [ ] All files pass `mypy` type checking
- [ ] No TODO comments left in code
- [ ] All public APIs have docstrings
- [ ] Code follows existing patterns

### No Regressions

- [ ] All existing 5244+ tests pass
- [ ] No breaking changes to existing tools
- [ ] No import errors in existing code
- [ ] Existing tool functionality unchanged

---

## Phase Complete When

All checkboxes above are checked, and:

1. `pytest tests/` passes with no failures
2. `mypy src/code_forge/tools/` reports no errors
3. `ruff check src/code_forge/tools/` reports no issues
4. TaskTool can spawn an explore agent
5. WebSearchBaseTool can perform a search
6. WebFetchBaseTool can fetch a URL
7. All tools appear in tool registry list

---

## Sign-Off

| Component | Completed | Date | Notes |
|-----------|-----------|------|-------|
| TaskTool | [ ] | | |
| WebSearchBaseTool | [ ] | | |
| WebFetchBaseTool | [ ] | | |
| Registration | [ ] | | |
| RAG Integration | [ ] | | |
| Tests | [ ] | | |
| Final Verification | [ ] | | |
