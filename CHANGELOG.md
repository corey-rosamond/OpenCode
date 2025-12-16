# Changelog

All notable changes to Code-Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
