# Changelog

All notable changes to Code-Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
