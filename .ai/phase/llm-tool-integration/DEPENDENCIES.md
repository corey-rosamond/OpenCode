# FEAT-002: Multi-Agent Tools & Web Search Integration - Dependencies

**Phase:** llm-tool-integration
**Version Target:** 1.10.0

---

## Phase Dependencies

This phase depends on the following completed phases:

| Phase | Reason |
|-------|--------|
| `specialized-agents` (v1.6.0) | Provides 20+ agent types that TaskTool will spawn |
| `agent-workflows` (v1.7.0) | Provides AgentManager infrastructure |
| `per-project-rag` (v1.9.0) | Provides RAGManager for context augmentation |

---

## Internal Dependencies

### Modules This Phase Uses

| Module | Dependency |
|--------|------------|
| `code_forge.tools.base` | BaseTool, ToolCategory, ToolParameter, ToolResult |
| `code_forge.tools.registry` | ToolRegistry for registration |
| `code_forge.agents.base` | AgentContext |
| `code_forge.agents.manager` | AgentManager for spawning agents |
| `code_forge.agents.types` | AgentTypeRegistry for type lookup |
| `code_forge.web.search` | SearchManager for web search |
| `code_forge.web.fetch` | Fetcher for web fetching |
| `code_forge.rag.manager` | RAGManager for context |

### Modules That Will Use This Phase

| Module | Usage |
|--------|-------|
| `code_forge.cli.main` | Tools registered at startup |
| `code_forge.langchain.tools` | LangChain tool adaptation |

---

## External Dependencies

### No New Dependencies

This phase does not introduce any new external dependencies. It wraps existing functionality:

- Web search uses existing `duckduckgo-search`, `googlesearch-python` (already optional)
- Web fetch uses existing `aiohttp`, `beautifulsoup4` (already in dependencies)
- Agent spawning uses existing `langchain` infrastructure

---

## Dependency Graph

```
TaskTool
  ├── tools/base.py (BaseTool, ToolResult)
  ├── tools/registry.py (ToolRegistry)
  ├── agents/manager.py (AgentManager)
  ├── agents/types.py (AgentTypeRegistry)
  ├── agents/base.py (AgentContext)
  └── rag/manager.py (RAGManager, optional)

WebSearchBaseTool
  ├── tools/base.py (BaseTool, ToolResult)
  ├── tools/registry.py (ToolRegistry)
  └── web/search/ (SearchManager, existing providers)

WebFetchBaseTool
  ├── tools/base.py (BaseTool, ToolResult)
  ├── tools/registry.py (ToolRegistry)
  └── web/fetch/ (Fetcher, existing implementation)
```

---

## Import Structure

### TaskTool Imports

```python
from code_forge.tools.base import BaseTool, ToolCategory, ToolParameter, ToolResult
from code_forge.tools.registry import ToolRegistry
from code_forge.agents.base import AgentContext
from code_forge.agents.manager import AgentManager
from code_forge.agents.types import AgentTypeRegistry
```

### WebSearchBaseTool Imports

```python
from code_forge.tools.base import BaseTool, ToolCategory, ToolParameter, ToolResult
from code_forge.tools.registry import ToolRegistry
from code_forge.web.search import SearchManager
```

### WebFetchBaseTool Imports

```python
from code_forge.tools.base import BaseTool, ToolCategory, ToolParameter, ToolResult
from code_forge.tools.registry import ToolRegistry
from code_forge.web.fetch import Fetcher
```

---

## Pre-Implementation Checklist

- [x] Verify `specialized-agents` phase is complete (v1.6.0)
- [x] Verify `agent-workflows` phase is complete (v1.7.0)
- [x] Verify `per-project-rag` phase is complete (v1.9.0)
- [x] Verify AgentManager.spawn() exists and works
- [x] Verify SearchManager exists in web/search/
- [x] Verify Fetcher exists in web/fetch/
- [x] Verify BaseTool pattern is established
- [x] Verify ToolRegistry singleton works
