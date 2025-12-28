# Changelog

All notable changes to Code-Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.9.0] - 2025-12-28

### Added
- **FEAT-001: Per-Project RAG Support (Complete)**
  - **Phase 4: Manager & Commands**
    - `RAGManager` - Central coordinator for all RAG operations
    - `RAGStatus` - Status information dataclass
    - CLI commands: `/rag index`, `/rag search`, `/rag status`, `/rag clear`, `/rag config`
    - `RAGContextAugmenter` - Integration with ContextManager for LLM context
    - `RAGMessageProcessor` - Determines when to augment context
  - **Phase 5: Integration & Polish**
    - RAGManager integrated into `Dependencies` and `CommandContext`
    - Auto-index on project open when RAG is enabled with `auto_index: true`
    - Context augmentation in message flow - queries enhanced with relevant project context
    - RAG commands registered with built-in command system
  - 348 total RAG tests, 90%+ coverage across all phases

## [1.8.15] - 2025-12-28

### Fixed
- **CLI-003: Token Counter Fix**: Fixed streaming token counter showing 0/200000
  - Updated `langchain/llm.py` to pass `usage_metadata` through streaming chunks
  - Updated `langchain/agent.py` to handle both dict and object access patterns for usage metadata
  - Token count now updates correctly after each streaming response

## [1.8.14] - 2025-12-28

### Improved
- **ARCH-004: Configuration System Consolidation**: Unified config patterns to use Pydantic
  - Migrated MCP config models (MCPServerConfig, MCPSettings, MCPConfig) to Pydantic BaseModel
  - Migrated Hook model in hooks/registry.py to Pydantic BaseModel
  - Migrated PermissionRule in permissions/models.py to Pydantic BaseModel
  - All config models now use consistent Pydantic patterns with validation
  - Eliminated duplicate MCPServerConfig dataclass in mcp/config.py
  - Loaders (MCPConfigLoader, HookConfig, PermissionConfig) remain for file I/O
  - Backward compatible: to_dict() and from_dict() methods preserved

## [1.8.13] - 2025-12-28

### Added
- **CLI-002: Output Format Options**: Added CLI flags for output customization
  - `--no-color` flag to disable colored output
  - `-q` / `--quiet` flag for reduced output verbosity
  - `--json` flag for machine-readable JSON output
  - Added `color`, `quiet`, and `json_output` fields to DisplayConfig
  - JSON mode outputs structured response with tool calls and stats
  - Quiet mode suppresses welcome message and completion stats

## [1.8.12] - 2025-12-28

### Added
- **SESS-002: Token Cache Monitoring**: Added cache configuration and monitoring
  - Added `token_cache_size` config option in SessionConfig (100-10000, default 1000)
  - Added `/session cache` command to view cache statistics
  - Added `--clear` flag to clear the cache
  - Added `get_cache_stats()` and `clear_cache()` methods to ContextManager
  - Shows hits, misses, size, and hit rate percentage

## [1.8.11] - 2025-12-28

### Fixed
- **TOOL-009: Edit Tool Preserves File Encoding**: Added automatic encoding detection
  - Added chardet dependency for encoding detection
  - Edit tool now detects file encoding before reading
  - Writes back with the same encoding to preserve original format
  - Supports UTF-8, UTF-16, Latin-1, Windows-1252, and other common encodings
  - Falls back to UTF-8 for unknown or empty files

## [1.8.10] - 2025-12-28

### Fixed
- **TOOL-010: Exception Details Sanitized**: Sanitized error messages to prevent system info leakage
  - `base.py`: Generic exception handler now shows only exception type
  - `file/utils.py`: Path validation errors no longer expose OS error details
  - `bash.py`: Working directory errors sanitized
  - `grep.py`, `glob.py`: File access errors sanitized
  - `write.py`: OS errors no longer expose filesystem details
  - `kill_shell.py`: Shell kill errors sanitized

## [1.8.9] - 2025-12-28

### Added
- **MCP-016: Circular Dependency Detection in Skills**: Added dependency support and cycle detection
  - Added `dependencies` field to `SkillDefinition` for declaring skill dependencies
  - Added `CircularDependencyError` exception for clear error reporting
  - Added `_detect_circular_dependency()` method using DFS algorithm
  - Added `validate_all_dependencies()` for bulk validation after loading
  - Added `check_dependencies` parameter to `register()` for bulk loading scenarios
  - Prevents infinite loops from circular skill references

## [1.8.8] - 2025-12-28

### Added
- **SESS-007: Session Cleanup Command**: Added `/session cleanup` command
  - Removes sessions older than N days (default 30)
  - Keeps minimum number of recent sessions (default 10)
  - Also cleans up old backup files
  - Usage: `/session cleanup [--days N] [--keep N]`

## [1.8.7] - 2025-12-28

### Added
- **CODE-005: Constants Module**: Created centralized constants for magic numbers
  - New `src/code_forge/core/constants.py` with timeouts, retries, size limits
  - Documented purpose of each constant
  - New code should use these constants for consistency

## [1.8.6] - 2025-12-28

### Improved
- **CODE-004: Lock Audit**: Audited threading.Lock usage across codebase
  - Confirmed threading.Lock is appropriate for singleton instantiation and quick counter updates
  - Added documentation comments in llm/client.py explaining lock choice
  - Audit found 23 lock usages, all appropriate for their use cases

## [1.8.5] - 2025-12-27

### Improved
- **CODE-003: Version Synchronization**: Single-source version using importlib.metadata
  - Version is now derived automatically from pyproject.toml
  - No longer need to update version in multiple files
  - Updated documentation in .ai/START.md

## [1.8.4] - 2025-12-27

### Removed
- **CODE-002: Dead Code Removal**: Removed unused WebConfig and related configuration classes
  - Deleted src/code_forge/web/config.py (WebConfig, SearchConfig, FetchConfig, CacheConfig, SearchProviderConfig)
  - Removed corresponding tests and exports

## [1.8.3] - 2025-12-27

### Added
- **CICD-001: CI/CD Pipeline**: Added GitHub Actions workflows for automated testing and releases
  - test.yml: pytest, mypy, ruff checks on Python 3.11 and 3.12
  - pr-check.yml: PR title format and CHANGELOG update validation
  - release.yml: automated GitHub releases on version tags
  - Issue templates for bug reports and feature requests
  - PR template for consistent pull request format

## [1.8.2] - 2025-12-27

### Fixed
- **CODE-001: ToolCategory Enum**: Added missing UTILITY category to ToolCategory enum
  - Fixes test fixtures in tests/conftest.py that reference ToolCategory.UTILITY

## [1.8.1] - 2025-12-27

### Fixed
- **DOC-001: README Package References**: Fixed all code examples using wrong package name
  - Updated imports from `forge.*` to `code_forge.*` in README.md
  - Updated project structure diagram to show `src/code_forge/`
  - Fixed coverage and mypy paths in development section
  - Fixed imports in docs/development/plugins.md
  - Fixed example path in .ai/GUARDRAILS.md

## [1.8.0] - 2025-12-27

### Added
- **Comprehensive Test Coverage**: Achieved 85%+ test coverage with 4,898 tests
  - **CLI Setup Tests**: 38 tests for setup wizard flow
  - **Dependency Injection Tests**: 21 tests for DI container
  - **Agent Tests**: 712 tests covering all 20 built-in agent types
  - **Performance Benchmarks**: 18 benchmark tests for critical operations
  - **Test Documentation**: Comprehensive tests/README.md

### Fixed
- **Session Storage Deadlock**: Fixed recursive lock acquisition during corrupt file recovery
- **Config Observer Error**: Fixed AttributeError when notifying MagicMock observers
- **Git Test Types**: Fixed CommitInfo→GitCommit and sha→hash attribute names
- **MCP Client Types**: Fixed ServerCapabilities→MCPCapabilities type reference

### Improved
- Test suite now provides confidence for refactoring and feature development
- Performance benchmarks catch regressions in critical paths
- Test documentation guides contributors on testing patterns

## [1.7.0] - 2025-12-21

### Added
- **Agent Workflow System**: Multi-agent workflow orchestration with DAG-based execution
  - **Workflow Models**: WorkflowDefinition, WorkflowStep, WorkflowState with full type safety
  - **YAML Parser**: Define workflows in YAML with validation and schema checking
  - **Dependency Management**: DAG-based dependency resolution with cycle detection
  - **Parallel Execution**: Automatic parallel execution of independent steps
  - **Conditional Execution**: Boolean expressions for conditional step execution
  - **State Management**: Persistent workflow state with checkpoint/resume capability
  - **Workflow Executor**: Complete orchestration engine with error handling and retries
  - **Template Registry**: Built-in workflow templates with user/project override support
  - **7 Built-in Templates**: pr-review, bug-fix, feature-implementation, security-audit-full, code-quality-improvement, code-migration, parallel-analysis
  - **Slash Commands**: `/workflow list|run|status|resume|cancel` for workflow management
  - **LLM Tool**: WorkflowTool for AI-driven workflow discovery and execution

### Improved
- Workflow system enables complex multi-step development tasks with automatic coordination
- Checkpointing allows resuming failed workflows from last successful step
- Template system provides reusable workflows for common software development patterns
- DAG validation prevents invalid workflow configurations at parse time

## [1.6.0] - 2025-12-21

### Added
- **16 New Specialized Agent Types**: Expanded agent system from 4 to 20 agent types
  - **Coding Agents**: test-generation, documentation, refactoring, debug
  - **Writing & Communication Agents**: writing, communication, tutorial
  - **Visual & Design Agents**: diagram
  - **Testing & QA Agents**: qa-manual
  - **Research & Analysis Agents**: research, log-analysis, performance-analysis
  - **Security & Dependencies Agents**: security-audit, dependency-analysis
  - **Project Management Agents**: migration-planning, configuration

### Improved
- Agent system now covers comprehensive software development workflows beyond just code exploration
- Each agent type has specialized system prompts optimized for its domain
- Tool access restrictions tailored to each agent's purpose for better security
- Resource limits configured per agent type based on typical usage patterns

## [1.5.0] - 2025-12-21

### Fixed
- **Session File Locking**: Added cross-platform file locking (fcntl/msvcrt) to prevent concurrent access corruption
- **Permission Rate Limiting**: Added DoS protection with sliding window rate limiter (10 denials/60s, 5min backoff)
- **Hook Retry Logic**: Added exponential backoff retry for transient failures (OSError, ConnectionError, TimeoutError)

### Added
- **Hook Dry-Run Mode**: Simulate hook execution without running commands for testing

## [1.4.0] - 2025-12-21

### Improved
- **Test Quality**: Replaced 116 weak assertions with specific type checks across 53 test files
- **Test Coverage**: Added 35+ parametrized tests generating 150+ test cases
- **Concurrency Tests**: Added 23 concurrent/race condition tests for thread safety validation

## [1.3.0] - 2025-12-17

### Fixed
- Streaming response error handling - API errors during streaming no longer cause "Attempted to access streaming response content" crash

## [1.2.0] - 2025-12-17

### Added
- **Setup Wizard**: First-time API key configuration wizard for new users

### Fixed
- ReadTool line limit now properly stops reading after limit reached
- SSRF protection added to URL fetcher with private IP range detection
- API keys no longer exposed in logs (wrapped with SecretStr)
- Agent no longer makes double API calls (fixed streaming tool assembly)
- Shell output buffers now bounded to prevent memory issues

### Changed
- Reorganized `.ai/` documentation structure

## [1.1.0] - 2025-12-10

### Changed
- **Project Rename**: Renamed from OpenCode to Code-Forge

### Fixed
- Help text URL updated to point to correct repository

## [1.0.0] - 2025-12-09

### Added

#### Core Features
- **Multi-Model Support**: Access 400+ AI models via OpenRouter API including Claude, GPT-4, Llama, Mistral, and more
- **Interactive REPL**: Rich terminal interface with syntax highlighting and auto-completion
- **Session Management**: Persistent sessions with automatic save/resume capability
- **Context Management**: Intelligent token counting with multiple truncation strategies

#### Tool System
- **File Tools**: Read, Write, Edit, Glob, Grep for comprehensive file operations
- **Execution Tools**: Bash, BashOutput, KillShell for shell command execution
- **Web Tools**: WebFetch, WebSearch for web content retrieval
- **Tool Permissions**: Allow/Ask/Deny permission levels with pattern matching

#### Integrations
- **LangChain Integration**: ReAct-style agent executor with tool loop
- **Git Integration**: Safe git operations with built-in guardrails
- **GitHub Integration**: Issues, PRs, and Actions workflow management
- **MCP Protocol Support**: Connect to external MCP tool servers

#### Extensibility
- **Plugin System**: Extend functionality with custom plugins
- **Hooks System**: Pre/post execution hooks for customization
- **Skills System**: Activate specialized skills for domain-specific tasks
- **Subagents**: Autonomous agents for complex multi-step tasks

#### Commands
- Session management: `/session list|new|resume|delete|title`
- Context management: `/context compact|reset`
- Configuration: `/config get|set`, `/model`
- Debug: `/debug`, `/tokens`, `/history`, `/tools`
- Plugin management: `/plugins list|info|enable|disable|reload`
- Skill activation: `/skill <name>|off|info|list`

### Performance
- Cold start: < 2 seconds
- Tool overhead: < 100ms
- Memory usage: < 500MB typical
- 90%+ test coverage

### Documentation
- Installation guide
- Quick start tutorial
- User guide with command reference
- Tool reference documentation
- Plugin development guide
- Architecture documentation

### Security
- Path traversal prevention in file tools
- Dangerous command blocking in Bash tool
- Permission system with user confirmation
- Git safety guards for destructive operations

## [0.1.0] - 2025-12-02

### Added
- Initial project structure
- Core interfaces and types
- Basic configuration system

---

## Release Notes

### v1.0.0 Highlights

Code-Forge 1.0.0 is the first stable release, featuring a complete AI-powered coding assistant with:

- **400+ AI Models**: Connect to any model via OpenRouter
- **Powerful Tools**: Read, write, edit files, run commands, search the web
- **Safe Operations**: Permission system and git safety guards
- **Extensible**: Plugin and hooks system for customization
- **Persistent Sessions**: Save and resume conversations

### Upgrade Notes

This is the initial stable release. No upgrade path from pre-release versions.

### Known Issues

- Web search requires network connectivity
- Large file editing (>10MB) may be slow
- Some MCP servers may have compatibility issues

### Contributors

Thanks to all contributors who made this release possible!
