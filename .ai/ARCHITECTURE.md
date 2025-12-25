# Code-Forge Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (cli/repl.py)                      │
├─────────────────────────────────────────────────────────────┤
│                  LangChain Agent (langchain/)               │
├──────────────────┬──────────────────┬───────────────────────┤
│   Tool System    │  Permission Sys  │    Hooks System       │
│   (tools/)       │  (permissions/)  │    (hooks/)           │
├──────────────────┴──────────────────┴───────────────────────┤
│                  OpenRouter Client (llm/)                   │
├─────────────────────────────────────────────────────────────┤
│              Core Foundation (core/, config/)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Overview

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **Core** | `core/` | Interfaces, types, errors, logging |
| **Config** | `config/` | Configuration loading and models |
| **CLI** | `cli/` | REPL, themes, status bar |
| **Tools** | `tools/` | File ops, bash execution |
| **LLM** | `llm/` | OpenRouter client, streaming |
| **LangChain** | `langchain/` | Agent executor, memory, callbacks |
| **Permissions** | `permissions/` | Rule-based permission checking |
| **Hooks** | `hooks/` | Event-driven lifecycle hooks |
| **Sessions** | `sessions/` | Conversation persistence |
| **Context** | `context/` | Token counting, truncation |
| **Commands** | `commands/` | Slash command system |
| **Modes** | `modes/` | Plan, Thinking, Headless modes |
| **Agents** | `agents/` | Subagent spawning and management |
| **Skills** | `skills/` | Domain-specific skill bundles |
| **MCP** | `mcp/` | Model Context Protocol client |
| **Web** | `web/` | Search and fetch tools |
| **Git** | `git/` | Git operations and safety |
| **GitHub** | `github/` | GitHub API integration |
| **Plugins** | `plugins/` | Plugin discovery and loading |
| **Workflows** | `workflows/` | Multi-step agent pipelines and orchestration |

---

## Key Design Patterns

| Pattern | Where Used | Purpose |
|---------|------------|---------|
| **Singleton** | `ToolRegistry`, `SessionManager`, `HookRegistry` | Global state management |
| **Command** | `BaseTool`, `Command` | Encapsulate operations |
| **Template Method** | `BaseTool.execute()` | Standard execution flow |
| **Strategy** | Truncation strategies | Interchangeable algorithms |
| **Observer** | Hooks system | Event-driven communication |
| **Factory** | `AgentConfig.for_type()` | Complex object creation |
| **Adapter** | `LangChainToolAdapter` | Interface compatibility |

---

## Data Flow: User Input to Response

```
1. User types in REPL (cli/repl.py)
2. If /command → CommandExecutor (commands/executor.py)
3. Else → CodeForgeAgent.stream() (langchain/agent.py)
4. Agent calls LLM via OpenRouterLLM (langchain/llm.py)
5. LLM returns tool calls → Agent executes tools
6. Tool checks permissions (permissions/checker.py)
7. Tool fires hooks (hooks/executor.py)
8. Tool executes (tools/*/*)
9. Results back to LLM for next iteration
10. Final response streamed to user
```

---

## Extension Points

| To Add... | Implement... | Register In... |
|-----------|--------------|----------------|
| New Tool | `BaseTool` subclass | `tools/__init__.py` |
| New Command | `Command` subclass | `commands/builtin/` |
| New Agent Type | `Agent` subclass | `agents/types.py` |
| New Skill | YAML/MD file | `~/.forge/skills/` |
| New Mode | `Mode` subclass | `modes/manager.py` |
| New Hook | Config entry | `~/.forge/hooks.yaml` |
| New Plugin | Plugin class + manifest | `~/.forge/plugins/` |

---

## Key Interfaces

```python
# All tools implement this
class BaseTool(ABC):
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    async def _execute(self, context, **kwargs) -> ToolResult

# All commands implement this
class Command(ABC):
    name: str
    description: str
    category: CommandCategory
    async def execute(self, args, kwargs, context) -> CommandResult

# All agents implement this
class Agent(ABC):
    agent_type: str
    async def execute(self) -> AgentResult
```

---

## Thread Safety

All singletons use `threading.RLock`:
- `ToolRegistry._lock`
- `CommandRegistry._lock`
- `SessionManager._lock`
- `HookRegistry._lock`
- `SkillRegistry._lock`
- `PluginRegistry._lock`

Always acquire lock before modifying shared state.
