# FEAT-002: Multi-Agent Tools & Web Search Integration - Test Strategy

**Phase:** llm-tool-integration
**Version Target:** 1.10.0

---

## Test Structure

```
tests/
├── unit/
│   └── tools/
│       ├── task/
│       │   ├── __init__.py
│       │   └── test_task.py           # TaskTool tests
│       └── web/
│           ├── __init__.py
│           ├── test_search.py         # WebSearchBaseTool tests
│           └── test_fetch.py          # WebFetchBaseTool tests
└── integration/
    └── tools/
        ├── __init__.py
        ├── test_tool_registration.py  # Registration tests
        └── test_llm_tool_access.py    # LLM integration tests
```

---

## Unit Tests

### test_task.py

```python
"""Tests for TaskTool."""

class TestTaskTool:
    def test_name_property(self):
        """TaskTool.name returns 'Task'."""

    def test_category_property(self):
        """TaskTool.category returns ToolCategory.TASK."""

    def test_description_property(self):
        """TaskTool.description is informative."""

    def test_get_parameters(self):
        """get_parameters returns required parameters."""

    def test_agent_type_parameter(self):
        """agent_type parameter is required string."""

    def test_task_parameter(self):
        """task parameter is required string."""

    def test_wait_parameter(self):
        """wait parameter is optional boolean."""

    def test_use_rag_parameter(self):
        """use_rag parameter is optional boolean."""


class TestTaskToolExecution:
    @pytest.fixture
    def mock_agent_manager(self):
        """Mock AgentManager for testing."""

    async def test_spawn_explore_agent(self, mock_agent_manager):
        """Can spawn explore agent type."""

    async def test_spawn_plan_agent(self, mock_agent_manager):
        """Can spawn plan agent type."""

    async def test_spawn_code_review_agent(self, mock_agent_manager):
        """Can spawn code-review agent type."""

    async def test_spawn_security_audit_agent(self, mock_agent_manager):
        """Can spawn security-audit agent type."""

    async def test_spawn_test_generation_agent(self, mock_agent_manager):
        """Can spawn test-generation agent type."""

    async def test_unknown_agent_type_error(self, mock_agent_manager):
        """Returns error for unknown agent type."""

    async def test_returns_agent_result(self, mock_agent_manager):
        """Returns agent's result output."""


class TestTaskToolRAGIntegration:
    async def test_receives_rag_from_context(self):
        """TaskTool receives RAGManager from context."""

    async def test_passes_rag_to_agent(self):
        """RAGManager is passed to spawned agent."""

    async def test_rag_disabled_with_flag(self):
        """RAGManager not passed when use_rag=false."""

    async def test_works_without_rag(self):
        """Works when RAGManager is None."""


class TestTaskToolErrorHandling:
    async def test_agent_spawn_failure(self):
        """Handles agent spawn failure gracefully."""

    async def test_agent_execution_failure(self):
        """Handles agent execution failure gracefully."""

    async def test_missing_agent_type(self):
        """Returns error when agent_type missing."""

    async def test_missing_task(self):
        """Returns error when task missing."""
```

### test_search.py

```python
"""Tests for WebSearchBaseTool."""

class TestWebSearchBaseTool:
    def test_name_property(self):
        """WebSearchBaseTool.name returns 'WebSearch'."""

    def test_category_property(self):
        """WebSearchBaseTool.category returns ToolCategory.WEB."""

    def test_description_property(self):
        """WebSearchBaseTool.description is informative."""

    def test_get_parameters(self):
        """get_parameters returns all parameters."""

    def test_query_parameter_required(self):
        """query parameter is required."""

    def test_num_results_parameter_optional(self):
        """num_results parameter is optional."""

    def test_provider_parameter_optional(self):
        """provider parameter is optional."""


class TestWebSearchExecution:
    @pytest.fixture
    def mock_search_manager(self):
        """Mock SearchManager for testing."""

    async def test_basic_search(self, mock_search_manager):
        """Performs basic search with query."""

    async def test_search_with_limit(self, mock_search_manager):
        """Respects num_results parameter."""

    async def test_search_with_provider(self, mock_search_manager):
        """Uses specified provider."""

    async def test_search_with_allowed_domains(self, mock_search_manager):
        """Filters by allowed domains."""

    async def test_search_with_blocked_domains(self, mock_search_manager):
        """Filters out blocked domains."""

    async def test_formats_results(self, mock_search_manager):
        """Formats results for LLM consumption."""


class TestWebSearchErrorHandling:
    async def test_no_results(self):
        """Returns appropriate message for no results."""

    async def test_network_error(self):
        """Handles network errors gracefully."""

    async def test_provider_error(self):
        """Handles provider errors gracefully."""

    async def test_missing_query(self):
        """Returns error when query missing."""
```

### test_fetch.py

```python
"""Tests for WebFetchBaseTool."""

class TestWebFetchBaseTool:
    def test_name_property(self):
        """WebFetchBaseTool.name returns 'WebFetch'."""

    def test_category_property(self):
        """WebFetchBaseTool.category returns ToolCategory.WEB."""

    def test_description_property(self):
        """WebFetchBaseTool.description is informative."""

    def test_get_parameters(self):
        """get_parameters returns all parameters."""

    def test_url_parameter_required(self):
        """url parameter is required."""

    def test_format_parameter_optional(self):
        """format parameter is optional with default."""

    def test_use_cache_parameter_optional(self):
        """use_cache parameter is optional."""

    def test_timeout_parameter_optional(self):
        """timeout parameter is optional."""


class TestWebFetchExecution:
    @pytest.fixture
    def mock_fetcher(self):
        """Mock Fetcher for testing."""

    async def test_fetch_as_markdown(self, mock_fetcher):
        """Fetches and converts to markdown."""

    async def test_fetch_as_text(self, mock_fetcher):
        """Fetches and converts to plain text."""

    async def test_fetch_as_raw(self, mock_fetcher):
        """Fetches raw HTML."""

    async def test_uses_cache(self, mock_fetcher):
        """Uses cache when enabled."""

    async def test_bypasses_cache(self, mock_fetcher):
        """Bypasses cache when disabled."""

    async def test_respects_timeout(self, mock_fetcher):
        """Applies timeout to request."""


class TestWebFetchErrorHandling:
    async def test_invalid_url(self):
        """Returns error for invalid URL."""

    async def test_network_error(self):
        """Handles network errors gracefully."""

    async def test_timeout_error(self):
        """Handles timeout errors gracefully."""

    async def test_missing_url(self):
        """Returns error when url missing."""
```

---

## Integration Tests

### test_tool_registration.py

```python
"""Tests for tool registration."""

class TestToolRegistration:
    def test_task_tool_registered(self):
        """TaskTool is registered after register_all_tools()."""

    def test_web_search_tool_registered(self):
        """WebSearchBaseTool is registered."""

    def test_web_fetch_tool_registered(self):
        """WebFetchBaseTool is registered."""

    def test_no_registration_conflicts(self):
        """No tool name conflicts."""

    def test_all_tools_accessible(self):
        """All tools can be retrieved by name."""

    def test_tools_in_tool_list(self):
        """All tools appear in list_tools()."""
```

### test_llm_tool_access.py

```python
"""Tests for LLM tool access."""

class TestLLMToolAccess:
    async def test_llm_can_call_task_tool(self):
        """LLM can invoke TaskTool."""

    async def test_llm_can_call_search_tool(self):
        """LLM can invoke WebSearchBaseTool."""

    async def test_llm_can_call_fetch_tool(self):
        """LLM can invoke WebFetchBaseTool."""

    async def test_tool_results_returned_to_llm(self):
        """Tool results are returned to LLM."""
```

---

## Test Fixtures

### Mock Providers

```python
class MockAgentManager:
    """Mock AgentManager for TaskTool tests."""

    async def spawn_and_execute(self, agent_type, task, **kwargs):
        return MockAgentResult(output=f"Executed {agent_type}: {task}")


class MockSearchManager:
    """Mock SearchManager for WebSearch tests."""

    async def search(self, query, **kwargs):
        return [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."},
        ]


class MockFetcher:
    """Mock Fetcher for WebFetch tests."""

    async def fetch(self, url, **kwargs):
        return "# Page Content\n\nThis is the page content."
```

---

## Test Coverage Targets

| Module | Target Coverage |
|--------|-----------------|
| `tools/task/__init__.py` | 100% |
| `tools/task/task.py` | 95% |
| `tools/web/__init__.py` | 100% |
| `tools/web/search.py` | 95% |
| `tools/web/fetch.py` | 95% |
| **Overall** | **>90%** |

---

## Test Commands

```bash
# Run all new tool tests
pytest tests/unit/tools/task tests/unit/tools/web -v

# Run with coverage
pytest tests/unit/tools/task tests/unit/tools/web \
  --cov=src/code_forge/tools/task \
  --cov=src/code_forge/tools/web \
  --cov-report=term-missing

# Run integration tests
pytest tests/integration/tools -v

# Run specific test file
pytest tests/unit/tools/task/test_task.py -v

# Run all tests (verify no regressions)
pytest tests/ -v
```

---

## CI Integration

These tests run as part of the existing test workflow. No special configuration needed since they follow existing patterns.
