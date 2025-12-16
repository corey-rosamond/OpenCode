# Code-Forge

An AI-powered CLI development assistant with access to 400+ AI models via OpenRouter API and LangChain 1.0 integration for agent orchestration.

## Quick Start

```bash
# Clone and install
git clone git@github.com:corey-rosamond/Code-Forge.git
cd Code-Forge
./install.sh

# Set your API key
export OPENROUTER_API_KEY=your-key-here

# Run
forge
```

## Features

- **Multi-Model Access**: Connect to 400+ AI models through OpenRouter API
- **LangChain Integration**: ReAct-style agent executor with tool loop
- **Comprehensive Tool System**: File operations, shell execution, pattern matching
- **Permission System**: Granular control with glob patterns, regex, and rule hierarchies
- **Hooks System**: Execute custom shell commands on lifecycle events
- **Interactive REPL**: Rich terminal UI with themes and status bar
- **Session Management**: Persistent conversations with JSON storage and auto-save
- **Context Management**: Token counting, truncation strategies, and context compaction
- **Slash Commands**: Extensible command system with built-in commands for session, context, config, and debugging
- **Operating Modes**: Plan, Thinking, and Headless modes for structured task execution
- **Subagents System**: Spawn autonomous agents for complex, multi-step tasks
- **Skills System**: Domain-specific capabilities via reusable skill bundles
- **MCP Protocol Support**: Connect to Model Context Protocol servers for extended capabilities
- **Web Tools**: Search and fetch web content with caching and format conversion
- **Git Integration**: Repository operations, status, history, diff, and safety guards
- **GitHub Integration**: Issues, pull requests, reviews, actions, and repository management
- **Plugin System**: Extensible architecture with plugin discovery, loading, and lifecycle management

## Installation

### Automatic Installation (Recommended)

```bash
git clone git@github.com:corey-rosamond/Code-Forge.git
cd Code-Forge
./install.sh
```

The install script will:
- Create a virtual environment at `~/.forge/venv`
- Install Code-Forge and all dependencies
- Add the `forge` command to your PATH
- Optionally update your shell configuration

### Manual Installation

```bash
# Clone the repository
git clone git@github.com:corey-rosamond/Code-Forge.git
cd Code-Forge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### Update

```bash
# Check for updates
forge check-update

# Update to latest version
forge update
```

Or manually:
```bash
cd Code-Forge
./update.sh
```

### Uninstall

```bash
./uninstall.sh
```

## Usage

```bash
# Start interactive REPL
forge

# Show version
forge --version

# Show help
forge --help
```

## Project Structure

```
Code-Forge/
├── src/forge/           # Source code
│   ├── core/               # Core interfaces, types, errors, logging
│   ├── config/             # Configuration system
│   ├── cli/                # REPL, themes, status bar
│   ├── tools/              # Tool system
│   │   ├── file/           # Read, Write, Edit, Glob, Grep tools
│   │   └── execution/      # Bash, BashOutput, KillShell tools
│   ├── llm/                # OpenRouter client, streaming
│   ├── langchain/          # LangChain integration, agent, prompts
│   ├── permissions/        # Permission checker, rules, prompts
│   ├── hooks/              # Event hooks, executor
│   ├── sessions/           # Session management and persistence
│   ├── context/            # Context management and token counting
│   ├── commands/           # Slash command system
│   ├── modes/              # Operating modes (Plan, Thinking, Headless)
│   ├── agents/             # Subagents system
│   ├── skills/             # Skills system
│   ├── mcp/                # MCP protocol support
│   ├── web/                # Web tools (search, fetch)
│   ├── git/                # Git integration
│   ├── github/             # GitHub integration
│   └── plugins/            # Plugin system
├── tests/                  # Test suite (3400+ tests)
└── .ai/                    # AI planning documentation
```

## Tool System

### File Tools

```python
from forge.tools.file import ReadTool, WriteTool, EditTool, GlobTool, GrepTool

# Read files with offset/limit support
read = ReadTool()
result = await read.execute(file_path="/path/to/file.py")

# Write files with automatic directory creation
write = WriteTool()
result = await write.execute(file_path="/path/to/new.py", content="...")

# Edit files with find/replace
edit = EditTool()
result = await edit.execute(
    file_path="/path/to/file.py",
    old_string="def old_func",
    new_string="def new_func",
)

# Glob pattern matching
glob = GlobTool()
result = await glob.execute(pattern="**/*.py")

# Content search with regex
grep = GrepTool()
result = await grep.execute(pattern="class.*Tool", path="/src")
```

### Execution Tools

```python
from forge.tools.execution import BashTool, BashOutputTool, KillShellTool

# Execute shell commands
bash = BashTool()
result = await bash.execute(command="ls -la", timeout=30000)

# Run in background
result = await bash.execute(command="pytest", run_in_background=True)

# Get background output
output = BashOutputTool()
result = await output.execute(bash_id="abc123")

# Kill background process
kill = KillShellTool()
result = await kill.execute(shell_id="abc123")
```

## Permission System

```python
from forge.permissions import PermissionChecker, PermissionLevel

checker = PermissionChecker()

# Check if tool execution is allowed
result = checker.check("bash", {"command": "ls"})
if result.level == PermissionLevel.ALLOWED:
    # Execute tool
    pass
elif result.level == PermissionLevel.ASK:
    # Prompt user for confirmation
    pass
elif result.level == PermissionLevel.DENIED:
    # Block execution
    pass
```

## Hooks System

Execute custom shell commands in response to lifecycle events.

### Event Types

| Category | Events |
|----------|--------|
| Tool | `tool:pre_execute`, `tool:post_execute`, `tool:error` |
| LLM | `llm:pre_request`, `llm:post_response`, `llm:stream_start`, `llm:stream_end`, `llm:error` |
| Session | `session:start`, `session:end`, `session:save`, `session:load` |
| Permission | `permission:check`, `permission:denied` |
| User | `user:input`, `user:abort` |

### Example Configuration

```json
{
  "hooks": [
    {
      "event": "tool:pre_execute:bash",
      "command": "echo \"Executing: $FORGE_TOOL_NAME\"",
      "timeout": 5.0
    },
    {
      "event": "session:start",
      "command": "notify-send 'Code-Forge' 'Session started'"
    }
  ]
}
```

### Programmatic Usage

```python
from forge.hooks import HookRegistry, HookExecutor, HookEvent, Hook, fire_event

# Register a hook
registry = HookRegistry.get_instance()
registry.register(Hook(
    event_pattern="tool:pre_execute",
    command="echo 'Executing tool: $FORGE_TOOL_NAME'",
    timeout=10.0,
))

# Fire an event
event = HookEvent.tool_pre_execute("bash", {"command": "ls"})
results = await fire_event(event)

# Check if operation should continue
for result in results:
    if not result.should_continue:
        print(f"Blocked by hook: {result.hook.event_pattern}")
```

## Session Management

```python
from forge.sessions import SessionManager, Session

# Get singleton manager instance
manager = SessionManager.get_instance()

# Create a new session
session = manager.create(
    title="My Session",
    model="anthropic/claude-3-5-sonnet",
    tags=["python", "api"],
)

# Add messages
manager.add_message("user", "Hello!")
manager.add_message("assistant", "Hi there!")

# Record tool calls
manager.record_tool_call(
    tool_name="bash",
    arguments={"command": "ls"},
    result={"output": "file.py"},
    duration=0.05,
)

# Update token usage
manager.update_usage(prompt_tokens=100, completion_tokens=50)

# Save and close
manager.close()

# Later, resume the session
resumed = manager.resume(session.id)

# Or resume the most recent session
latest = manager.resume_latest()

# List sessions
summaries = manager.list_sessions(limit=10, tags=["python"])
```

### Session Lifecycle Hooks

```python
# Register hooks for session events
manager.register_hook("session:start", lambda s: print(f"Started: {s.id}"))
manager.register_hook("session:end", lambda s: print(f"Ended: {s.id}"))
manager.register_hook("session:message", lambda s, m: print(f"Message: {m.role}"))
manager.register_hook("session:save", lambda s: print(f"Saved: {s.id}"))
```

## Context Management

```python
from forge.context import ContextManager, TruncationMode

# Create context manager for a model
manager = ContextManager(
    model="anthropic/claude-3-opus",
    mode=TruncationMode.SMART,
    auto_truncate=True,
)

# Set system prompt
prompt_tokens = manager.set_system_prompt("You are a helpful assistant.")

# Add messages
manager.add_message({"role": "user", "content": "Hello!"})
manager.add_message({"role": "assistant", "content": "Hi there!"})

# Check usage
print(f"Token usage: {manager.token_usage}")
print(f"Usage: {manager.usage_percentage:.1f}%")
print(f"Available: {manager.available_tokens}")
print(f"Near limit: {manager.is_near_limit}")

# Get messages for LLM request (includes system prompt)
messages = manager.get_context_for_request()

# Get statistics
stats = manager.get_stats()

# Reset context
manager.reset()
```

### Truncation Modes

| Mode | Description |
|------|-------------|
| `SLIDING_WINDOW` | Keep N most recent messages |
| `TOKEN_BUDGET` | Remove oldest messages to fit budget |
| `SMART` | Preserve first and last messages, remove middle |
| `SUMMARIZE` | Use LLM to summarize old messages |

### Token Counting

```python
from forge.context import get_counter, TiktokenCounter, ApproximateCounter

# Get appropriate counter for model
counter = get_counter("claude-3-opus")

# Count tokens in text
tokens = counter.count("Hello, world!")

# Count tokens in messages
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
]
total = counter.count_messages(messages)

# Direct counter usage
tiktoken = TiktokenCounter(model="gpt-4")
approx = ApproximateCounter(tokens_per_word=1.3)
```

### Truncation Strategies

```python
from forge.context import (
    SlidingWindowStrategy,
    TokenBudgetStrategy,
    SmartTruncationStrategy,
    CompositeStrategy,
)

# Sliding window (keep last N messages)
sliding = SlidingWindowStrategy(window_size=20, preserve_system=True)
truncated = sliding.truncate(messages, target_tokens, counter)

# Token budget (fit within token limit)
budget = TokenBudgetStrategy(preserve_system=True)
truncated = budget.truncate(messages, target_tokens, counter)

# Smart truncation (keep first and last messages)
smart = SmartTruncationStrategy(
    preserve_first=2,
    preserve_last=10,
    preserve_system=True,
)
truncated = smart.truncate(messages, target_tokens, counter)

# Composite (chain strategies)
composite = CompositeStrategy([smart, budget])
truncated = composite.truncate(messages, target_tokens, counter)
```

### Storage

Sessions are stored as JSON files in:
- Default: `~/.local/share/forge/sessions/`
- Project-local: `.forge/sessions/`

## Slash Commands

Code-Forge provides an extensible slash command system for quick actions within the REPL.

### Built-in Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `/help` | `/h`, `/?` | Show help for commands |
| `/commands` | | List all available commands |
| `/session` | `/s`, `/sess` | Session management (list, new, resume, delete, title, tag) |
| `/context` | `/ctx`, `/c` | Context management (compact, reset, mode) |
| `/config` | `/cfg` | Configuration management (get, set) |
| `/model` | | Change or show current model |
| `/clear` | `/cls` | Clear the screen |
| `/exit` | `/quit`, `/q` | Exit the REPL |
| `/reset` | | Reset conversation context |
| `/stop` | | Stop current operation |
| `/debug` | `/dbg` | Toggle debug mode |
| `/tokens` | | Show token usage |
| `/history` | | Show message history |
| `/tools` | | List available tools |

### Usage Examples

```bash
# Get help on a command
/help session

# List recent sessions
/session list

# Resume a session by ID
/session resume abc123

# Create a new titled session
/session new --title "API Refactoring"

# Compact conversation context
/context compact

# Change truncation mode
/context mode smart

# View/set configuration
/config get llm.model
/config set llm.temperature 0.8

# Check token usage
/tokens

# Toggle debug output
/debug
```

### Programmatic Usage

```python
from forge.commands import CommandRegistry, CommandExecutor, CommandContext

# Get command registry
registry = CommandRegistry.get_instance()

# List all commands
for cmd in registry.list_commands():
    print(f"/{cmd.name}: {cmd.description}")

# Search commands
results = registry.search("session")

# Execute a command
executor = CommandExecutor(registry)
context = CommandContext(session_manager=manager, config=config)
result = await executor.execute("/session list", context)

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

## Operating Modes

Code-Forge supports different operating modes that modify assistant behavior for specialized tasks.

### Available Modes

| Mode | Description |
|------|-------------|
| Normal | Default mode with no modifications |
| Plan | Structured planning with task breakdown and dependency tracking |
| Thinking | Extended reasoning with visible thinking process |
| Headless | Non-interactive mode for automation and CI/CD |

### Programmatic Usage

```python
from forge.modes import ModeManager, ModeContext, ModeName, setup_modes

# Set up all default modes
manager = setup_modes()

# Create context for mode operations
context = ModeContext(session=session, config=config, output=print)

# Switch to plan mode
manager.switch_mode(ModeName.PLAN, context)

# Get current mode
current = manager.get_current_mode()
print(f"Current mode: {current.name.value}")

# Modify system prompt for current mode
prompt = manager.get_system_prompt("You are a helpful assistant.")

# Switch back to normal mode
manager.switch_mode(ModeName.NORMAL, context)
```

### Plan Mode

```python
from forge.modes import PlanMode, Plan, PlanStep

mode = PlanMode()

# Create a plan
plan = Plan(
    title="API Refactoring",
    summary="Refactor REST API to use async handlers",
    steps=[
        PlanStep(number=1, description="Update dependencies", files=["requirements.txt"]),
        PlanStep(number=2, description="Convert handlers to async", dependencies=[1]),
        PlanStep(number=3, description="Update tests", dependencies=[2]),
    ],
    considerations=["Backwards compatibility", "Performance testing"],
    success_criteria=["All tests pass", "No sync handlers remain"],
)

# Set plan and convert to markdown
mode.set_plan(plan)
print(mode.show_plan())

# Convert to todos for execution
todos = mode.execute_plan()
```

### Thinking Mode

```python
from forge.modes import ThinkingMode, ThinkingConfig

# Configure thinking mode
config = ThinkingConfig(
    max_thinking_tokens=10000,
    show_thinking=True,
    deep_mode=True,
)

mode = ThinkingMode(thinking_config=config)

# Process response with thinking extraction
response = "<thinking>Analysis...</thinking><response>Final answer</response>"
formatted = mode.modify_response(response)

# Get last thinking result
result = mode.get_last_thinking()
if result:
    print(f"Thinking time: {result.time_seconds:.1f}s")
```

### Headless Mode

```python
from forge.modes import HeadlessMode, HeadlessConfig, OutputFormat

# Configure headless mode for CI/CD
config = HeadlessConfig(
    input_file="task.txt",
    output_file="result.json",
    output_format=OutputFormat.JSON,
    timeout=300,
    auto_approve_safe=True,
    fail_on_unsafe=True,
)

mode = HeadlessMode(headless_config=config)

# Create execution result
result = mode.create_result(
    success=True,
    message="Task completed",
    output="Generated code...",
    details={"files_modified": 3},
)

# Write result to configured output
mode.write_output(result)
```

## Configuration

Configuration is loaded from multiple sources with precedence:

1. Environment variables (`FORGE_*`)
2. Project config (`.forge/config.toml`)
3. Global config (`~/.config/forge/config.toml`)

### Example Configuration

```toml
[llm]
model = "anthropic/claude-3-5-sonnet"
temperature = 0.7
max_tokens = 4096

[permissions]
default_level = "ask"

[hooks]
enabled = true
```

## Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src/forge --cov-report=term-missing

# Type checking (strict mode)
mypy src/forge/

# Linting
ruff check src/forge/

# Format code
ruff format src/forge/
```

### Quality Gates

All code must pass:
- **mypy**: Strict mode with no errors
- **ruff**: No linting violations
- **pytest**: All tests passing
- **coverage**: Minimum 90% code coverage

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (REPL)                          │
├─────────────────────────────────────────────────────────────┤
│                    LangChain Agent                          │
├──────────────────┬──────────────────┬───────────────────────┤
│   Tool System    │  Permission Sys  │     Hooks System      │
├──────────────────┼──────────────────┼───────────────────────┤
│   File Tools     │   Rule Matcher   │   Event Executor      │
│   Exec Tools     │   Checker        │   Registry            │
├──────────────────┴──────────────────┴───────────────────────┤
│                   OpenRouter Client                         │
├─────────────────────────────────────────────────────────────┤
│                    Core Foundation                          │
│            (Interfaces, Types, Errors, Logging)             │
└─────────────────────────────────────────────────────────────┘
```

## Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 1.1 | Core Foundation | Complete |
| 1.2 | Configuration System | Complete |
| 1.3 | Basic REPL Shell | Complete |
| 2.1 | Tool System Foundation | Complete |
| 2.2 | File Tools | Complete |
| 2.3 | Execution Tools | Complete |
| 3.1 | OpenRouter Client | Complete |
| 3.2 | LangChain Integration | Complete |
| 4.1 | Permission System | Complete |
| 4.2 | Hooks System | Complete |
| 5.1 | Session Management | Complete |
| 5.2 | Context Management | Complete |
| 6.1 | Slash Commands | Complete |
| 6.2 | Operating Modes | Complete |
| 7.1 | Subagents System | Complete |
| 7.2 | Skills System | Complete |
| 8.1 | MCP Protocol Support | Complete |
| 8.2 | Web Tools | Complete |
| 9.1 | Git Integration | Complete |
| 9.2 | GitHub Integration | Complete |
| 10.1 | Plugin System | Complete |
| 10.2 | Polish & Integration | Complete |

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please read the planning documentation in `.ai/` before making significant changes.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all quality gates pass
5. Submit a pull request
