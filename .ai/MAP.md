# Code-Forge: Code Map

Quick reference for finding things in the codebase.

---

## Source Structure

```
src/code_forge/
├── __init__.py          # Package version
├── __main__.py          # python -m code_forge entry
├── core/                # Foundation layer
│   ├── interfaces.py    # ITool, IModelProvider, IConfigLoader, ISessionRepository
│   ├── types.py         # Core type definitions
│   ├── errors.py        # Exception hierarchy (CodeForgeError base)
│   └── logging.py       # get_logger() function
├── config/              # Configuration
│   ├── models.py        # CodeForgeConfig, ModelConfig, etc.
│   ├── sources.py       # EnvSource, FileSource, DefaultSource
│   └── loader.py        # ConfigLoader.load_all()
├── cli/                 # Command line interface
│   ├── main.py          # main() entry point, run_with_agent()
│   ├── repl.py          # CodeForgeREPL class
│   ├── themes.py        # Theme definitions
│   ├── status.py        # StatusBar widget
│   └── setup.py         # First-run setup wizard
├── tools/               # Tool system
│   ├── base.py          # BaseTool, ToolParameter, ToolResult, ExecutionContext
│   ├── registry.py      # ToolRegistry singleton
│   ├── executor.py      # ToolExecutor
│   ├── file/            # File tools
│   │   ├── read.py      # ReadTool
│   │   ├── write.py     # WriteTool
│   │   ├── edit.py      # EditTool
│   │   ├── glob.py      # GlobTool
│   │   ├── grep.py      # GrepTool
│   │   └── utils.py     # Security utilities
│   └── execution/       # Execution tools
│       ├── bash.py      # BashTool
│       ├── bash_output.py   # BashOutputTool
│       ├── kill_shell.py    # KillShellTool
│       └── shell_manager.py # ShellManager singleton
├── llm/                 # LLM client
│   ├── models.py        # Message, ToolCall, CompletionRequest/Response
│   ├── errors.py        # LLMError hierarchy
│   ├── client.py        # OpenRouterClient
│   ├── streaming.py     # StreamCollector
│   └── routing.py       # Model routing and limits
├── langchain/           # LangChain integration
│   ├── llm.py           # OpenRouterLLM (BaseChatModel)
│   ├── agent.py         # CodeForgeAgent, AgentEvent, AgentResult
│   ├── tools.py         # LangChainToolAdapter
│   ├── memory.py        # ConversationMemory
│   ├── messages.py      # Message conversion
│   ├── callbacks.py     # Callback handlers
│   └── prompts.py       # System prompt generation
├── permissions/         # Permission system
│   ├── models.py        # PermissionLevel, PermissionRule, PermissionResult
│   ├── rules.py         # PatternMatcher, RuleSet
│   ├── checker.py       # PermissionChecker
│   ├── prompt.py        # User confirmation prompts
│   └── config.py        # DEFAULT_RULES
├── hooks/               # Event hooks
│   ├── events.py        # EventType, HookEvent
│   ├── registry.py      # HookRegistry, Hook
│   ├── executor.py      # HookExecutor, fire_event()
│   └── config.py        # HookConfig, HOOK_TEMPLATES
├── sessions/            # Session management
│   ├── models.py        # Session, SessionMessage, ToolInvocation
│   ├── storage.py       # SessionStorage (JSON files)
│   ├── index.py         # SessionIndex, SessionSummary
│   └── manager.py       # SessionManager singleton
├── context/             # Context management
│   ├── tokens.py        # TokenCounter, TiktokenCounter
│   ├── limits.py        # ContextBudget, ContextLimits
│   ├── strategies.py    # TruncationStrategy implementations
│   ├── compaction.py    # ContextCompactor
│   └── manager.py       # ContextManager
├── commands/            # Slash commands
│   ├── parser.py        # CommandParser
│   ├── base.py          # Command ABC, CommandResult
│   ├── registry.py      # CommandRegistry singleton
│   ├── executor.py      # CommandExecutor
│   └── builtin/         # Built-in commands
│       ├── help_commands.py     # /help, /commands
│       ├── session_commands.py  # /session
│       ├── context_commands.py  # /context
│       ├── control_commands.py  # /clear, /exit, /reset
│       ├── config_commands.py   # /config, /model
│       └── debug_commands.py    # /debug, /tokens, /tools
├── modes/               # Operating modes
│   ├── base.py          # Mode ABC, ModeConfig, ModeName
│   ├── manager.py       # ModeManager singleton
│   ├── prompts.py       # Mode-specific prompts
│   ├── plan.py          # PlanMode
│   ├── thinking.py      # ThinkingMode
│   └── headless.py      # HeadlessMode
├── agents/              # Subagent system
│   ├── base.py          # Agent ABC, AgentState, ResourceLimits
│   ├── types.py         # AgentTypeDefinition, AgentTypeRegistry
│   ├── result.py        # AgentResult
│   ├── executor.py      # AgentExecutor
│   ├── manager.py       # AgentManager singleton
│   └── builtin/         # Built-in agents
├── skills/              # Skills system
│   ├── base.py          # Skill, SkillDefinition, SkillMetadata
│   ├── parser.py        # SkillParser (YAML/MD)
│   ├── loader.py        # SkillLoader
│   ├── registry.py      # SkillRegistry singleton
│   ├── commands.py      # /skill command
│   └── builtin/         # Built-in skills
├── mcp/                 # MCP protocol
│   ├── protocol.py      # MCPRequest, MCPResponse, MCPTool
│   ├── transport/       # Transport implementations
│   ├── client.py        # MCPClient
│   ├── tools.py         # MCPToolAdapter
│   ├── config.py        # MCPConfig
│   └── manager.py       # MCPManager singleton
├── web/                 # Web tools
│   ├── types.py         # SearchResult, FetchResponse
│   ├── config.py        # WebConfig
│   ├── cache.py         # WebCache
│   ├── tools.py         # WebSearchTool, WebFetchTool
│   ├── search/          # Search providers
│   └── fetch/           # URL fetcher
├── git/                 # Git integration
│   ├── repository.py    # GitRepository
│   ├── status.py        # GitStatus
│   ├── history.py       # GitHistory
│   ├── diff.py          # GitDiff
│   ├── safety.py        # GitSafety checks
│   ├── operations.py    # GitOperations
│   └── context.py       # GitContext for LLM
├── github/              # GitHub integration
│   ├── auth.py          # GitHubAuth
│   ├── client.py        # GitHubClient
│   ├── repository.py    # RepositoryService
│   ├── issues.py        # IssueService
│   ├── pull_requests.py # PullRequestService
│   ├── actions.py       # ActionsService
│   └── context.py       # GitHubContext for LLM
├── plugins/             # Plugin system
│   ├── base.py          # Plugin ABC
│   ├── manifest.py      # PluginManifest
│   ├── discovery.py     # PluginDiscovery
│   ├── loader.py        # PluginLoader
│   ├── registry.py      # PluginRegistry
│   ├── manager.py       # PluginManager singleton
│   └── commands.py      # /plugins command
└── workflows/           # Workflow system
    ├── models.py        # WorkflowDefinition, StepDefinition
    ├── graph.py         # WorkflowGraph, DAG validation
    ├── parser.py        # YAML workflow parser
    ├── conditions.py    # Conditional execution logic
    ├── executor.py      # WorkflowExecutor
    ├── state.py         # WorkflowState, checkpointing
    ├── registry.py      # WorkflowRegistry singleton
    ├── tool.py          # WorkflowTool for LLM
    └── commands.py      # /workflow command
```

---

## Common Tasks: Where to Look

| Task | Primary Files |
|------|---------------|
| Add a new tool | `tools/base.py`, `tools/__init__.py` |
| Add a slash command | `commands/base.py`, `commands/builtin/` |
| Modify LLM behavior | `langchain/agent.py`, `langchain/prompts.py` |
| Change permission rules | `permissions/config.py`, `permissions/rules.py` |
| Add lifecycle hook | `hooks/events.py`, `hooks/config.py` |
| Modify REPL UI | `cli/repl.py`, `cli/themes.py`, `cli/status.py` |
| Change config loading | `config/loader.py`, `config/sources.py` |
| Add truncation strategy | `context/strategies.py` |
| Add operating mode | `modes/base.py`, `modes/manager.py` |
| Add agent type | `agents/types.py`, `agents/builtin/` |
| Add skill | `skills/builtin/` or `~/.forge/skills/` |
| Add MCP server support | `mcp/config.py`, `mcp/manager.py` |
| Add workflow template | `workflows/registry.py`, `~/.forge/workflows/` |

---

## Test Structure

Tests mirror source structure:
```
tests/
├── unit/           # Unit tests (isolated, mocked)
│   ├── core/
│   ├── cli/
│   ├── llm/
│   ├── tools/
│   └── ...
├── integration/    # Integration tests (components together)
├── agents/         # Agent-specific tests
├── commands/       # Command tests
├── mcp/            # MCP tests
├── git/            # Git tests
├── github/         # GitHub tests
├── web/            # Web tools tests
├── skills/         # Skills tests
├── plugins/        # Plugin tests
└── conftest.py     # Shared fixtures
```
