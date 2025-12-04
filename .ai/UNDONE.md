# OpenCode Project Roadmap

**Project:** OpenCode - Claude Code Alternative
**Target:** Production-ready CLI using OpenRouter API and LangChain 1.0
**Last Updated:** 2025-12-05

---

## Phase Overview

| Phase | Name | Planning | Implementation | Testing |
|-------|------|----------|----------------|---------|
| 1.1 | Core Foundation | ✅ Done | ✅ Done | ✅ Done |
| 1.2 | Configuration System | ✅ Done | ✅ Done | ✅ Done |
| 1.3 | Basic REPL Shell | ✅ Done | ✅ Done | ✅ Done |
| 2.1 | Tool System Foundation | ✅ Done | ✅ Done | ✅ Done |
| 2.2 | File Tools | ✅ Done | ✅ Done | ✅ Done |
| 2.3 | Execution Tools | ✅ Done | ✅ Done | ✅ Done |
| 3.1 | OpenRouter Client | ✅ Done | ✅ Done | ✅ Done |
| 3.2 | LangChain Integration | ✅ Done | ✅ Done | ✅ Done |
| 4.1 | Permission System | ✅ Done | ✅ Done | ✅ Done |
| 4.2 | Hooks System | ✅ Done | ✅ Done | ✅ Done |
| 5.1 | Session Management | ✅ Done | ✅ Done | ✅ Done |
| 5.2 | Context Management | ✅ Done | ✅ Done | ✅ Done |
| 6.1 | Slash Commands | ✅ Done | ✅ Done | ✅ Done |
| 6.2 | Operating Modes | ✅ Done | ✅ Done | ✅ Done |
| 7.1 | Subagents System | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 7.2 | Skills System | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 8.1 | MCP Protocol Support | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 8.2 | Web Tools | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 9.1 | Git Integration | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 9.2 | GitHub Integration | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 10.1 | Plugin System | ✅ Done | ⬜ Not Started | ⬜ Not Started |
| 10.2 | Polish and Integration Testing | ✅ Done | ⬜ Not Started | ⬜ Not Started |

---

## What Exists

### Planning Documents (Complete)

All 22 phases have planning documents in `.ai/phase/[phase]/`:

- `PLAN.md` - Architectural design with code examples
- `COMPLETION_CRITERIA.md` - Acceptance criteria checklists
- `GHERKIN.md` - Behavior specifications
- `DEPENDENCIES.md` - Phase dependencies
- `TESTS.md` - Test strategies
- `REVIEW.md` - Review checklists

**Code quality review has been applied to all PLAN.md files** (~50+ fixes for thread safety, security, resource management, etc.)

### Implementation Code

Phase 1.1 implementation complete in `src/opencode/`:
- Core interfaces (`core/interfaces.py`)
- Value objects (`core/types.py`)
- Exception hierarchy (`core/errors.py`)
- Logging infrastructure (`core/logging.py`)
- Result type (`utils/result.py`)
- CLI entry point (`cli/main.py`)

Phase 1.2 implementation complete in `src/opencode/config/`:
- Configuration models (`config/models.py`)
- Configuration sources (`config/sources.py`)
- Configuration loader (`config/loader.py`)

Phase 1.3 implementation complete in `src/opencode/cli/`:
- Theme definitions (`cli/themes.py`)
- Status bar (`cli/status.py`)
- REPL core (`cli/repl.py`)
- CLI main updated to start REPL

Phase 2.1 implementation complete in `src/opencode/tools/`:
- Tool models and BaseTool ABC (`tools/base.py`)
- Thread-safe ToolRegistry singleton (`tools/registry.py`)
- ToolExecutor with tracking (`tools/executor.py`)
- Public exports (`tools/__init__.py`)

Phase 2.2 implementation complete in `src/opencode/tools/file/`:
- ReadTool - Read files with offset/limit, images, PDFs, notebooks (`tools/file/read.py`)
- WriteTool - Write files with directory creation (`tools/file/write.py`)
- EditTool - Find/replace with replace_all option (`tools/file/edit.py`)
- GlobTool - File pattern matching with excludes (`tools/file/glob.py`)
- GrepTool - Content search with regex, context lines (`tools/file/grep.py`)
- Security utilities - Path traversal prevention (`tools/file/utils.py`)

Phase 2.3 implementation complete in `src/opencode/tools/execution/`:
- ShellManager - Singleton for managing background shell processes (`tools/execution/shell_manager.py`)
- ShellProcess - Dataclass for tracking shell state and output (`tools/execution/shell_manager.py`)
- ShellStatus - Enum for process states (pending, running, completed, failed, killed, timeout)
- BashTool - Execute commands with timeout, background mode (`tools/execution/bash.py`)
- BashOutputTool - Retrieve output from background shells (`tools/execution/bash_output.py`)
- KillShellTool - Terminate background processes (`tools/execution/kill_shell.py`)
- Security patterns block dangerous commands (rm -rf /, mkfs, dd, fork bombs)

Phase 3.1 implementation complete in `src/opencode/llm/`:
- Message, ToolCall, ToolDefinition models (`llm/models.py`)
- CompletionRequest/Response models (`llm/models.py`)
- StreamChunk, StreamDelta for streaming (`llm/models.py`)
- LLMError hierarchy - Auth, RateLimit, ModelNotFound, etc. (`llm/errors.py`)
- RouteVariant enum and model alias resolution (`llm/routing.py`)
- OpenRouterClient with retry logic, streaming, usage tracking (`llm/client.py`)
- StreamCollector for assembling streamed responses (`llm/streaming.py`)

Phase 3.2 implementation complete in `src/opencode/langchain/`:
- OpenRouterLLM wrapper - BaseChatModel implementation (`langchain/llm.py`)
- Bidirectional message conversion - LangChain <-> OpenCode (`langchain/messages.py`)
- Tool adapters - LangChainToolAdapter, OpenCodeToolAdapter (`langchain/tools.py`)
- ConversationMemory, SlidingWindowMemory, SummaryMemory (`langchain/memory.py`)
- Callback handlers - TokenTracking, Logging, Streaming, Composite (`langchain/callbacks.py`)
- OpenCodeAgent - ReAct-style agent executor with tool loop (`langchain/agent.py`)

Phase 4.1 implementation complete in `src/opencode/permissions/`:
- Permission models - PermissionLevel, PermissionCategory, PermissionRule, PermissionResult (`permissions/models.py`)
- Pattern matching - PatternMatcher with glob, regex, tool/arg/category patterns (`permissions/rules.py`)
- RuleSet - Collection with priority/specificity-based evaluation (`permissions/rules.py`)
- PermissionChecker - Multi-source rule hierarchy (session > project > global) (`permissions/checker.py`)
- User confirmation - ConfirmationChoice, ConfirmationRequest, PermissionPrompt (`permissions/prompt.py`)
- Configuration - PermissionConfig, DEFAULT_RULES (14 rules) (`permissions/config.py`)

Phase 4.2 implementation complete in `src/opencode/hooks/`:
- Event types - EventType enum with 16 event types (tool, LLM, session, permission, user) (`hooks/events.py`)
- HookEvent - Event data with factory methods and serialization (`hooks/events.py`)
- Hook dataclass - Pattern matching (exact, glob, tool-specific, comma-separated) (`hooks/registry.py`)
- HookRegistry - Thread-safe singleton for hook management (`hooks/registry.py`)
- HookResult - Execution results with success/should_continue properties (`hooks/executor.py`)
- HookExecutor - Async shell command execution with timeout handling (`hooks/executor.py`)
- HookBlockedError - Exception for blocking pre-execution hooks (`hooks/executor.py`)
- fire_event() - Convenience function for firing events (`hooks/executor.py`)
- HookConfig - Configuration loading/saving (global + project) (`hooks/config.py`)
- HOOK_TEMPLATES - Example hooks (log_all, notify_session_start, git_auto_commit, block_sudo) (`hooks/config.py`)

Phase 5.1 implementation complete in `src/opencode/sessions/`:
- Session data models (`sessions/models.py`)
  - Session dataclass - Core session with messages, tool history, tokens, metadata
  - SessionMessage - Messages with to_llm_message()/from_llm_message() conversion
  - ToolInvocation - Tool call records with timing and success status
- Session storage (`sessions/storage.py`)
  - SessionStorage - File-based JSON persistence with atomic writes
  - Backup creation before overwrite, recovery support
  - XDG Base Directory compliance (~/.local/share/opencode/sessions/)
  - Automatic backup rotation (max 100, 7 days age limit)
- Session index (`sessions/index.py`)
  - SessionIndex - Fast session listing without loading full files
  - SessionSummary - Lightweight session metadata for listings
  - In-memory index backed by index.json with auto-rebuild on corruption
- Session manager (`sessions/manager.py`)
  - SessionManager - Singleton with thread-safe instance management
  - create(), resume(), save(), close(), delete() lifecycle methods
  - Auto-save with configurable interval (asyncio task)
  - Hook system integration (session:start, session:end, session:message, session:save)

Phase 5.2 implementation complete in `src/opencode/context/`:
- Token counting (`context/tokens.py`)
  - TokenCounter - Abstract base class for token counting
  - TiktokenCounter - tiktoken-based accurate counting with fallback
  - ApproximateCounter - Word-based approximation for unknown models
  - CachingCounter - LRU cache wrapper for performance
  - get_counter() - Factory function for model-appropriate counters
- Context limits (`context/limits.py`)
  - ContextBudget - Token allocation (system, conversation, tools, response)
  - ContextLimits - Model-specific context window limits
  - ContextTracker - Current usage monitoring and overflow detection
  - MODEL_LIMITS - Known limits for Claude, GPT, Llama, Mistral models
- Truncation strategies (`context/strategies.py`)
  - TruncationStrategy - Abstract base for truncation strategies
  - SlidingWindowStrategy - Keep N most recent messages
  - TokenBudgetStrategy - Remove oldest to fit token budget
  - SmartTruncationStrategy - Preserve first and last, add marker
  - SelectiveTruncationStrategy - Filter by role or marked messages
  - CompositeStrategy - Chain multiple strategies
- Context compaction (`context/compaction.py`)
  - ContextCompactor - LLM-based summarization of old messages
  - ToolResultCompactor - Truncate large tool outputs
- Context manager (`context/manager.py`)
  - TruncationMode - Enum for truncation mode selection
  - ContextManager - Central coordinator for context management
  - Auto-truncation, compact_if_needed(), get_stats()

Phase 6.1 implementation complete in `src/opencode/commands/`:
- Command parsing (`commands/parser.py`)
  - ParsedCommand - Dataclass for parsed command with args, kwargs, flags
  - CommandParser - Parses /command input, handles quoted strings
  - Levenshtein distance for command suggestions
- Command base (`commands/base.py`)
  - ArgumentType - Enum for argument types (string, integer, boolean, choice, path)
  - CommandArgument - Argument definition with validation
  - CommandResult - Execution result with success, output, error, data
  - CommandCategory - Enum for command categories
  - Command - ABC for command implementations with execute(), validate(), get_help()
  - SubcommandHandler - Base for commands with subcommands
- Command registry (`commands/registry.py`)
  - CommandRegistry - Thread-safe singleton for command registration
  - register(), unregister(), resolve() by name or alias
  - search(), list_commands(), get_categories()
- Command executor (`commands/executor.py`)
  - CommandContext - Execution context with session_manager, context_manager, config, etc.
  - CommandExecutor - Parses, validates, executes commands
  - register_builtin_commands() - Registers all built-in commands
- Built-in commands (`commands/builtin/`):
  - help_commands.py: /help, /commands (list and search commands)
  - session_commands.py: /session with subcommands (list, new, resume, delete, title, tag, untag)
  - context_commands.py: /context with subcommands (compact, reset, mode)
  - control_commands.py: /clear, /exit, /reset, /stop
  - config_commands.py: /config with subcommands (get, set), /model
  - debug_commands.py: /debug, /tokens, /history, /tools

Phase 6.2 implementation complete in `src/opencode/modes/`:
- Mode base classes (`modes/base.py`)
  - Mode - Abstract base class with activate/deactivate lifecycle
  - ModeConfig - Mode configuration with system prompt additions
  - ModeContext - Context for mode operations (session, config, output handler)
  - ModeState - Persistent mode state with serialization
  - NormalMode - Default mode with no modifications
  - ModeName - Enum for available modes (NORMAL, PLAN, THINKING, HEADLESS)
- Mode prompts (`modes/prompts.py`)
  - PLAN_MODE_PROMPT - System prompt for planning mode
  - THINKING_MODE_PROMPT - System prompt for thinking mode
  - THINKING_MODE_DEEP_PROMPT - Enhanced prompt for deep thinking
  - HEADLESS_MODE_PROMPT - System prompt for headless mode
  - get_mode_prompt() - Factory function for mode prompts
- Mode manager (`modes/manager.py`)
  - ModeManager - Thread-safe singleton for mode management
  - switch_mode() - Switch between modes with push/pop support
  - Mode stacking for temporary mode changes
  - Auto-activation via pattern matching
  - State save/restore for persistence
- Plan mode (`modes/plan.py`)
  - PlanMode - Mode for structured planning with task breakdown
  - Plan - Structured plan with steps, considerations, success criteria
  - PlanStep - Individual step with substeps, dependencies, files, complexity
  - PLANNING_PATTERNS - Regex patterns for auto-activation
  - Plan to markdown conversion for display
  - Plan to todos conversion for execution
- Thinking mode (`modes/thinking.py`)
  - ThinkingMode - Extended reasoning with visible thinking process
  - ThinkingConfig - Configuration (max tokens, show thinking, deep mode)
  - ThinkingResult - Separated thinking and response with metrics
  - THINKING_PATTERN - Regex for extracting <thinking>/<response> sections
  - should_suggest_thinking() - Pattern detection for complex problems
- Headless mode (`modes/headless.py`)
  - HeadlessMode - Non-interactive mode for automation/CI/CD
  - HeadlessConfig - File I/O, output format, timeout, auto-approve settings
  - HeadlessResult - Structured output with success, message, exit code
  - OutputFormat - Enum for TEXT/JSON output
  - create_headless_config_from_args() - Factory from CLI arguments
- Package exports (`modes/__init__.py`)
  - setup_modes() - Register all default modes with manager

### Tests

Phase 1.1 + 1.2 + 1.3 + 2.1 + 2.2 + 2.3 + 3.1 + 3.2 + 4.1 + 4.2 + 5.1 + 5.2 + 6.1 + 6.2 tests complete in `tests/`:
- 2035 tests passing (1795 previous + 240 new Operating Modes tests)
- 97% code coverage for modes package
- mypy strict mode passing
- ruff linting passing

---

## Next Steps

### Immediate Priority: Phase 7.1 Implementation (Subagents System)

Before starting Phase 7.1:
1. [x] Phase 1.1 complete (Core Foundation)
2. [x] Phase 1.2 complete (Configuration System)
3. [x] Phase 1.3 complete (Basic REPL Shell)
4. [x] Phase 2.1 complete (Tool System Foundation)
5. [x] Phase 2.2 complete (File Tools)
6. [x] Phase 2.3 complete (Execution Tools)
7. [x] Phase 3.1 complete (OpenRouter Client)
8. [x] Phase 3.2 complete (LangChain Integration)
9. [x] Phase 4.1 complete (Permission System)
10. [x] Phase 4.2 complete (Hooks System)
11. [x] Phase 5.1 complete (Session Management)
12. [x] Phase 5.2 complete (Context Management)
13. [x] Phase 6.1 complete (Slash Commands)
14. [x] Phase 6.2 complete (Operating Modes)
15. [ ] Read `.ai/phase/7.1/` planning documents
16. [ ] Understand subagents requirements

Phase 7.1 will implement:
1. [ ] Agent spawning and management
2. [ ] Inter-agent communication
3. [ ] Task delegation patterns
4. [ ] Agent lifecycle management

### Implementation Order

Phases must be implemented in dependency order:

```
Phase 1.1 (Core Foundation)
    ├── Phase 1.2 (Configuration)
    │   └── Phase 1.3 (REPL Shell)
    │       └── Phase 6.1 (Slash Commands)
    │           └── Phase 6.2 (Operating Modes)
    ├── Phase 2.1 (Tool System)
    │   ├── Phase 2.2 (File Tools)
    │   ├── Phase 2.3 (Execution Tools)
    │   │   └── Phase 9.1 (Git Integration)
    │   │       └── Phase 9.2 (GitHub Integration)
    │   ├── Phase 4.1 (Permission System)
    │   │   └── Phase 4.2 (Hooks System)
    │   ├── Phase 8.1 (MCP Protocol)
    │   └── Phase 8.2 (Web Tools)
    ├── Phase 3.1 (OpenRouter Client)
    │   └── Phase 3.2 (LangChain Integration)
    │       ├── Phase 5.2 (Context Management)
    │       └── Phase 7.1 (Subagents System)
    │           └── Phase 7.2 (Skills System)
    └── Phase 5.1 (Session Management)

Phase 10.1 (Plugin System) - Requires all above
Phase 10.2 (Polish & Testing) - Requires all above
```

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| ⬜ Not Started | No work has begun |
| 🔄 In Progress | Active development, not complete |
| ✅ Done | Implemented, tested, reviewed, merged |

**Important:** A phase is only "Done" when:
- All code is implemented per PLAN.md
- All tests pass per TESTS.md
- All completion criteria met per COMPLETION_CRITERIA.md
- Code review completed per REVIEW.md

---

## Version History

| Date | Changes |
|------|---------|
| 2025-12-05 | Phase 6.2 implementation complete (2035 tests) |
| 2025-12-05 | Phase 6.1 implementation complete (1795 tests) |
| 2025-12-04 | Phase 5.2 implementation complete (1584 tests) |
| 2025-12-04 | Phase 5.1 implementation complete (1433 tests) |
| 2025-12-03 | Phase 4.2 implementation complete (1247 tests) |
| 2025-12-03 | Phase 4.1 implementation complete (1112 tests) |
| 2025-12-03 | Phase 3.2 implementation complete (941 tests) |
| 2025-12-03 | Phase 3.1 implementation complete (784 tests) |
| 2025-12-03 | Phase 2.3 implementation complete (652 tests) |
| 2025-12-03 | Phase 2.2 implementation complete (539 tests) |
| 2025-12-03 | Phase 2.1 implementation complete (431 tests) |
| 2025-12-03 | Phase 1.3 implementation complete |
| 2025-12-03 | Phase 1.2 implementation complete |
| 2025-12-03 | Phase 1.1 implementation complete |
| 2025-12-02 | Initial roadmap created with accurate status |

---

## Notes

- Planning is complete for all phases
- Phase 1.1 implementation complete (2025-12-03)
- Do not mark anything as complete without verified evidence
- Each phase requires planning docs to be read before implementation starts
- Source code is in `src/opencode/` (standard Python src layout)
