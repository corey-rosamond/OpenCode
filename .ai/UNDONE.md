# Code-Forge: Current Work

**Last Updated:** 2025-12-17

---

## Active Tasks

_No active tasks._

---

## Recently Completed (P0)

#### BUG-001: ReadTool Line Limit Broken
**Status:** Fixed (2025-12-12)
**File:** `src/code_forge/tools/file/read.py:158`
**Fix:** Changed `continue` to `break` to stop reading after limit reached

#### SEC-001: No SSRF Protection in URL Fetcher
**Status:** Fixed (2025-12-12)
**File:** `src/code_forge/web/fetch/fetcher.py`
**Fix:** Added `validate_url_host()` with private IP range detection (127.x, 10.x, 172.16.x, 192.168.x, 169.254.x, IPv6 private)

#### SEC-002: API Keys Exposed in Logs/Repr
**Status:** Fixed (2025-12-12)
**Files:** `src/code_forge/github/auth.py`, `src/code_forge/web/config.py`
**Fix:** Wrapped token fields with `pydantic.SecretStr`, masked in `to_dict()` output

#### PERF-001: Agent Makes Double API Calls
**Status:** Fixed (2025-12-12)
**File:** `src/code_forge/langchain/agent.py`
**Fix:** Added `_assemble_tool_calls()` method to build tool calls from streamed chunks instead of re-calling API

#### PERF-002: Unbounded Shell Output Buffers
**Status:** Fixed (2025-12-12)
**File:** `src/code_forge/tools/execution/shell_manager.py`
**Fix:** Added `MAX_BUFFER_SIZE` (10MB) and `_append_to_buffer()` with circular buffer behavior

#### BUG-002: Streaming Response Error Handling
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/client.py:283-307`
**Fix:** Added `await response.aread()` before accessing `.text` or `.json()` on streaming responses

#### SEC-007: Missing Owner/Repo Parameters in GitHub Actions
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/github/actions.py:131-134`
**Note:** Code review incorrectly identified this - `list_runs()` already has `owner` and `repo` parameters

#### SEC-008: Command Injection via working_dir Parameter
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/execution/bash.py:119-122, 226-247`
**Fix:** Added `_validate_working_dir()` method that validates path exists, is a directory, and uses `Path.resolve()` for canonical paths

#### SEC-009: Infinite Recursion Risk in Stdio Transport
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/mcp/transport/stdio.py:168-205`
**Fix:** Replaced recursive `receive()` call with a while loop and added safety limit for consecutive empty lines

#### SEC-010: Unvalidated LLM Tool Arguments
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:213-258`
**Fix:** Added type validation (must be dict) and Pydantic schema validation against tool's `args_schema` before execution

#### SEC-011: Unsafe Plugin Entry Point Loading
**Status:** Documented (2025-12-17)
**File:** `src/code_forge/plugins/discovery.py:44-67, 135-160`
**Fix:** Added SECURITY WARNING in class and method docstrings, plus debug logging when loading entry points. True sandboxing is a future enhancement.

#### ARCH-001: Duplicate Type Definitions
**Status:** Fixed (2025-12-17)
**Files:** `src/code_forge/core/types.py`, `src/code_forge/tools/base.py`
**Fix:** Removed duplicate ToolParameter and ToolResult from core/types.py, now re-exports from tools/base.py for backwards compatibility

#### ARCH-002: Core Interfaces Not Implemented
**Status:** Fixed (2025-12-17)
**Files:** `src/code_forge/core/interfaces.py`, `src/code_forge/sessions/repository.py`
**Fix:** Updated interface documentation, simplified IModelProvider, created SessionRepository that implements ISessionRepository

#### TOOL-001: Timeout Units Inconsistent
**Status:** Fixed (2025-12-17)
**Files:** `src/code_forge/tools/execution/bash.py`
**Fix:** Added clear documentation explaining that BashTool uses milliseconds (LLM API convention) and converts to seconds for asyncio internally. Both defaults are 2 minutes.

#### TOOL-002: Missing JSON Error Handling in Notebook Read
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/read.py:253-266`
**Fix:** Added try-except for json.JSONDecodeError with line/column info, plus validation that notebook is a dict

#### TOOL-003: Glob Pattern Can Escape Working Directory
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/glob.py:113-148`
**Fix:** Reject absolute patterns and path traversal (..) in patterns, plus filter results to ensure they're within resolved base_path

---

## Backlog

### Critical Priority (P0)

_All critical issues have been addressed._

---

### High Priority (P1)

#### ARCH-003: Tight Coupling in CLI Entry Point
**Status:** Fixed (2025-12-17)
**Files:** `src/code_forge/cli/main.py`, `src/code_forge/cli/dependencies.py`
**Fix:** Created Dependencies container class with factory method. run_with_agent() now accepts optional deps parameter for injection. Protocols defined for ILLMClient and IAgent for testing.

#### ARCH-004: Configuration System Fragmentation
**Status:** Deferred
**Files:** `config/`, `mcp/config.py`, `hooks/config.py`, `permissions/config.py`, `web/config.py`
**Issue:** 6+ modules use different config patterns (Pydantic vs dataclass vs custom)
**Impact:** Inconsistent API, hard to compose/test configurations
**Note:** Large refactoring task requiring careful migration:
- config/models.py uses Pydantic (canonical)
- mcp/config.py uses dataclasses (MCPServerConfig duplicates Pydantic version)
- hooks/config.py and permissions/config.py use class methods
- web/config.py uses dataclasses (currently unused)
Migration plan: Create common base, migrate one module at a time with tests. Deferred to avoid breaking changes.

#### TOOL-004: Symlink Parameter Creates Escape Route
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/utils.py:9-59`
**Fix:** Removed `allow_symlinks` parameter entirely; symlinks are now always rejected for security

#### LLM-001: Streaming Errors Silently Skipped
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/client.py:193-236`
**Fix:** Track parse errors during streaming, log summary at end with error rate. Catches JSONDecodeError and structural errors.

#### LLM-002: Thread Cleanup Timeout Too Short
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/llm.py:260-270`
**Fix:** Increased join timeout from 1s to 10s, added warning if thread still alive after timeout.

#### LLM-003: Token Counter Race Condition
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/client.py:103-370`
**Fix:** Added threading.Lock to protect all token counter access (update, read, reset).

#### LLM-004: Tool Execution Has No Timeout
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:109,263-304`
**Fix:** Added tool_timeout parameter (default 30s), wrapped all tool invocations with asyncio.wait_for().

#### SEC-012: Broken Path Validation Logic
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/utils.py:9-66`
**Fix:** Removed redundant `..` check on original path parts. The resolved path comparison with base_dir is the actual security boundary. Added error handling for symlink check on non-existent paths and invalid base_dir.

#### SEC-013: Bare Exception in Stream Reading
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/execution/shell_manager.py:140-180`
**Fix:** Added specific OSError handling for pipe errors, log unexpected exceptions with type and message for debugging.

#### SEC-014: O(n^2) Buffer Concatenation
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/execution/shell_manager.py:33-103`
**Fix:** Changed from string concatenation to deque-based chunk storage. Appends are O(1), stdout_buffer/stderr_buffer properties compute string lazily on access.

#### SEC-015: Async Lock Initialization Race
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/execution/shell_manager.py:275-298`
**Fix:** Added explicit check for running event loop before creating lock. Raises clear RuntimeError if called from non-async context.

#### SEC-016: Unsafe None Handling in Tool IDs
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/messages.py:48`
**Fix:** Generate UUID if ID is None/empty: `id=tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"` to ensure tool result matching works.

#### SEC-017: Fragile Tool Name Parsing
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:420-447`
**Fix:** Added regex validation for tool names, log warnings for malformed data, use regex extraction instead of fragile string split. Skip tool calls that can't be parsed.

#### SEC-018: Missing Null Check in LoggingCallback
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/langchain/callbacks.py:154`
**Note:** Code already handles None check with ternary: `response.llm_output.get("usage", {}) if response.llm_output else {}`

#### SEC-019: Fragile Async-Sync Pattern
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/langchain/tools.py:103-116`
**Note:** Code already handles async context properly: checks for running loop, uses ThreadPoolExecutor when in async context. This is cleaner than nest_asyncio.

#### SEC-020: Complex Heuristic Tool Call Parsing
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:385-472`
**Fix:** Addressed with SEC-017 (regex tool name validation). Added logging for JSON parse failures. Invalid tool names are now skipped with clear error messages.

#### SEC-021: Substring Domain Matching
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/web/search/base.py:71-103`
**Fix:** Added `domain_matches()` helper with proper suffix matching. Now checks exact match or subdomain match (domain ends with ".pattern"), preventing attacks like "github.com.attacker.com".

#### SEC-022: Race Condition in SSRF Check
**Status:** Documented (2025-12-17)
**File:** `src/code_forge/web/fetch/fetcher.py:38-58`
**Issue:** DNS validation at fetch time doesn't prevent TOCTOU (DNS rebinding)
**Note:** Added detailed SECURITY NOTE in docstring explaining the vulnerability and mitigation complexity. Full fix requires custom aiohttp connector with IP pinning - deferred to future work.

#### SEC-023: Race Condition in Spinner Management
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/main.py:240-389`
**Fix:** Initialize `spinner = None` and `tool_spinner = None` before try block. Added existence checks before calling stop() in except and finally blocks.

#### SEC-024: Potential Data Loss in Session Auto-Save
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/manager.py:20-35, 77-78, 574-587`
**Fix:** Added atexit handler that saves all active sessions at exit. Added sync save attempt in __del__. Sessions tracked via WeakSet for automatic cleanup.

#### SEC-025: No Permission Gating on Commands
**Status:** Not applicable (2025-12-17)
**File:** `src/code_forge/commands/executor.py:81-134`
**Note:** The permission system is designed for AI-initiated tool execution, not user-initiated CLI commands. Commands like /help, /session are user actions and don't need AI permission checks. Adding permission checks would break expected user experience.

#### SEC-026: Command Injection in MCP Stdio Transport
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/mcp/transport/stdio.py:15-26, 68-75`
**Fix:** Added DANGEROUS_ENV_VARS list and warning when dangerous env vars (LD_PRELOAD, PYTHONPATH, etc.) are set in MCP config. Warns users to verify config is from trusted source.

---

### Medium Priority (P2)

#### CLI-001: No Stdin/Batch Input Support
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/main.py:77-87, 411-415`
**Fix:** Added stdin detection with sys.stdin.isatty(). Piped input is read and processed in batch mode, then exits.

#### CLI-002: No Output Format Options
**Status:** Deferred
**File:** `src/code_forge/cli/repl.py`
**Issue:** No `--json`, `--no-color`, `-q` quiet mode options
**Note:** Feature request requiring significant CLI restructuring. Deferred to future enhancement.

#### CLI-003: Generic Error Messages
**Status:** Fixed (2025-12-17)
**Files:** `src/code_forge/cli/main.py:95-100, 121-124`
**Fix:** Added "Hint:" messages with actionable suggestions for config errors and REPL errors.

#### CLI-004: No Command Timeout Handling
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/main.py:248-266`
**Fix:** Added 30-second timeout via asyncio.wait_for() for command execution with helpful error message.

#### CLI-005: Missing UTF-8 Input Validation
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/repl.py:507-515`
**Fix:** Added UTF-8 encode/decode validation before processing input. Also added validation in stdin reading.

#### CLI-006: Quote Parsing Falls Back Poorly
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/commands/parser.py:145-157`
**Fix:** Changed to raise ValueError with helpful message for unbalanced quotes instead of silently falling back to split().

#### SEC-027: Dangerous Command Regex Bypassable
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/execution/bash.py:37-55`
**Fix:** Improved patterns to catch piped/chained variants. Removed `$` anchors, added patterns for any flag order, added curl/wget pipe-to-shell detection.

#### SEC-028: Domain Filter Uses Substring Match
**Status:** Duplicate of SEC-021 (2025-12-17)
**File:** `src/code_forge/web/search/base.py:71-103`
**Note:** Already fixed in SEC-021. Added proper domain_matches() helper with suffix matching.

#### SEC-029: HTML Parser Doesn't Remove Event Handlers
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/web/fetch/parser.py:138-216`
**Fix:** Added _sanitize_element() method that removes all event handler attributes (on*) and javascript: URLs from href/src/action/etc. Applied to all elements in extract_main_content().

#### SEC-030: Permission Pattern Regex DoS Risk
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/permissions/rules.py:36-68`
**Fix:** Added MAX_PATTERN_LENGTH (500 chars), REDOS_PATTERNS detection for nested quantifiers. Patterns matching ReDoS vectors are rejected.

#### MEM-001: Conversation Memory Trim is O(n^2)
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/memory.py:181-187`
**Fix:** Calculate total tokens once, then subtract each removed message incrementally. Changed from O(n²) to O(n).

#### MEM-002: Summary Memory Keeps Last 10 Hardcoded
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/memory.py:267-268, 302-305`
**Fix:** Added `recent_messages_to_keep` parameter (default 10) to SummaryMemory. Now configurable per instance.

#### CFG-001: Memory Leak in ConfigLoader.__del__
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:309-319`
**Fix:** Wrapped stop_watching() in try/except to handle partially destroyed state. Added docstring explaining __del__ limitations.

#### CFG-002: Thread-Safety Issue in File Watcher
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:336-422`
**Fix:** Added debouncing (500ms window) via threading.Timer. Filter out temp files (.swp, .tmp, ~, .bak). Events schedule reload instead of calling directly.

#### CFG-003: Race Condition in ConfigLoader.load_all()
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:143-171`
**Fix:** Added logging for skipped/empty config sources. Added FileNotFoundError handler for TOCTOU race when file disappears between exists() and load().

#### CFG-004: Overly Broad Exception Handling
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:136-141, 224-237`
**Fix:** Changed to catch ValidationError explicitly in load_all() and validate(). Unexpected exceptions now propagate instead of being masked.

#### CFG-005: Shallow Copy in Config Merge
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:193-222`
**Fix:** Use copy.deepcopy() for base dict and all override values. Returned dict is now fully independent of inputs.

#### LLM-005: Retry Thundering Herd
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/client.py:288-308`
**Fix:** Added random jitter (0.5x to 1.5x) to retry wait times for both rate limits and timeouts.

#### LLM-006: Streaming Token Tracking Not Implemented
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:546-553`
**Fix:** Extract usage_metadata from LangChain chunks during streaming and accumulate token counts.

#### LLM-007: No Chunk Validation in Streaming
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/streaming.py:36-78`
**Fix:** Added hasattr checks before accessing chunk attributes. Malformed chunks are silently skipped to allow stream to continue.

#### LLM-008: No Retry Logic for Tool Failures
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:147-224`
**Fix:** Added _execute_tool_with_retry() helper with exponential backoff and jitter. Retries on TimeoutError, OSError, ConnectionError. Used in both run() and stream().

#### LLM-009: No Complex Type Support in Schema
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/tools.py:58-137`
**Fix:** Added `_param_to_field()` helper that handles enum constraints (Literal types), string length constraints (min_length/max_length), and numeric constraints (ge/le). All ToolParameter fields now properly converted to Pydantic schema.

#### GIT-001: Lossy UTF-8 Decoding in Cache
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/web/cache.py:217-227`
**Fix:** Changed from `errors="replace"` to `errors="surrogateescape"` to preserve non-UTF-8 bytes in a recoverable form.

#### GIT-002: Complex Rename Parsing in Diff
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/git/diff.py:251-276`
**Fix:** Replaced string manipulation with dedicated regex patterns for partial renames (dir/{old => new}/file) and simple renames.

#### GIT-003: Silent Parse Failures in Git Status
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/git/status.py:180-188`
**Fix:** Added logger and warning message when git status line format is unexpected, helping detect git porcelain format changes.

#### GIT-004: Fragile Commit Block Splitting
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/git/history.py:87-118`
**Fix:** Added ASCII record separator (\\x1e) as commit marker in format string. Split on marker instead of fragile double-newline regex.

#### GIT-005: Unchecked Null on Deleted Source Repo
**Status:** Already fixed
**File:** `src/code_forge/github/pull_requests.py:56-58`
**Note:** Code already uses `data.get("head", {}).get("repo")` check before accessing full_name.

#### SESS-001: Unhandled Exception in Hook System
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/manager.py:526-543`
**Fix:** Changed logger.error to logger.exception for full traceback. Added callback name to error message for debugging.

#### SESS-002: Memory Leak in Token Counter Caching
**Status:** Deferred
**File:** `src/code_forge/context/tokens.py:257-353`
**Issue:** Cache default `max_cache_size=1000` could cause memory issues
**Note:** Feature request for cache statistics monitoring. Current size is reasonable for most use cases.

#### SESS-003: Silent Failure in Setup Wizard
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/setup.py:87-95`
**Fix:** Return None on save failure instead of API key. Added clearer warning that key is NOT saved.

#### SESS-004: Missing Error Handling in Session Index Rebuild
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/index.py:179-208`
**Fix:** Added logging for corrupted sessions during rebuild. Summary shows count of corrupted sessions skipped.

#### SESS-005: No Validation in Message Adding
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/models.py:200-235`
**Fix:** Added VALID_ROLES frozenset and validation. Raises ValueError for invalid roles with helpful message.

#### SESS-006: Quadratic Token Counting
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/context/strategies.py:165-175`
**Fix:** Calculate token count once, subtract incrementally. Changed from O(n²) to O(n).

#### SESS-007: No Automatic Session Cleanup
**Status:** Deferred
**File:** `src/code_forge/sessions/storage.py:329-369`
**Issue:** `cleanup_old_sessions()` and `cleanup_old_backups()` exist but never called
**Note:** Feature request - requires implementing scheduled cleanup or CLI command.

#### SESS-008: No Conflict Detection for Concurrent Access
**Status:** Deferred
**File:** `src/code_forge/sessions/storage.py:141-195`
**Issue:** Multiple processes can write to same session file
**Note:** Feature request - requires implementing file locking (fcntl/msvcrt).

#### SESS-009: Missing Token Limit Enforcement
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/context/limits.py:274-285`
**Fix:** Added edge case handling for budget <= 0. Returns True if any conversation tokens exist when budget is exhausted.

#### PERM-001: Path Traversal in Glob Patterns
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/permissions/rules.py:184-206`
**Fix:** Added `_normalize_path_value()` method that uses `os.path.normpath()` to normalize path-like values before glob/regex matching, preventing traversal attacks like `/etc/../etc/passwd`.

#### PERM-002: Unvalidated Hook Environment Variables
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/hooks/executor.py:81-119, 245-255`
**Fix:** Added `DANGEROUS_ENV_VARS` blacklist (LD_PRELOAD, PYTHONPATH, etc.) and validation that logs warning and blocks dangerous env vars from hooks.

#### PERM-003: Thread-Safety of Session Rules
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/permissions/checker.py:64-65, 78-80, 157-184`
**Fix:** Added `threading.RLock` to PermissionChecker. All session_rules operations now protected by lock.

#### PERM-004: HookResult.should_continue Ignores Errors
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/hooks/executor.py:49-59`
**Fix:** Changed `should_continue` to return `self.exit_code == 0 and not self.timed_out and not self.error`, matching the `success` property logic.

#### PERM-005: No Audit Logging for Permission Decisions
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/permissions/checker.py:107-146`
**Fix:** Added `_audit_log()` method that logs permission decisions. DENY logs at WARNING, ASK at INFO, ALLOW at DEBUG level. Includes tool name, source (session/project/global/default), and rule pattern.

#### MCP-001: Race Condition in Agent Manager
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/agents/manager.py:292-305`
**Fix:** Made copy of `agent_ids` list within lock to prevent caller modifications affecting results during await.

#### MCP-002: Missing Dependency Validation in Plugins
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/plugins/manager.py:61-88, 111-119`
**Fix:** Added `_check_dependencies()` method using `importlib.metadata.version()` to check if dependencies are installed before loading plugins.

#### MCP-003: Missing Reconnection Logic
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/mcp/manager.py:153-256`
**Fix:** Implemented exponential backoff with jitter in `connect()` using `reconnect_attempts` and `reconnect_delay` from settings.

#### MCP-004: Missing Path Traversal Protection in Config Save
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/mcp/config.py:315-358`
**Fix:** Added `ALLOWED_SAVE_DIRS` and validation that resolved path is within `~/.forge` or `.forge` directories.

#### MCP-005: Potential Injection Through Skill Context Values
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/skills/base.py:319-356`
**Fix:** Added `MAX_CONTEXT_VALUE_LENGTH` (1000 chars) limit. Values are truncated before sanitization to prevent injection via very long strings.

---

### Low Priority (P3)

#### TEST-001: 555 Weak Assertions
**Status:** Fixed (2025-12-21)
**Location:** Throughout test suite
**Fix:** Replaced all 116 weak `assert is not None` with specific isinstance() type checks and value validations
**Commit:** a58961f

#### TEST-002: Only 1 Parametrized Test
**Status:** Fixed (2025-12-21)
**Location:** Tests throughout
**Fix:** Added 35+ parametrized tests across 9 files generating 150+ test cases covering HTTP codes, error scenarios, file formats, permission patterns
**Commit:** 8f0968f

#### TEST-003: No Concurrent/Race Condition Tests
**Status:** Fixed (2025-12-21)
**Location:** tests/integration/test_concurrency.py
**Fix:** Added 23 comprehensive concurrent/race condition tests covering registries, singletons, shared state, and cross-component concurrency
**Commit:** 5928cb4

#### TEST-004: providers/ Module Has No Tests
**Status:** Not applicable (2025-12-18)
**Location:** `src/code_forge/providers/`
**Issue:** Module exists but has no corresponding tests
**Note:** Module is a Phase 3.x placeholder containing only a docstring - no code to test

#### DOC-001: Fixture Dependency Chains Not Documented
**Status:** Fixed (2025-12-18)
**File:** `tests/conftest.py:9-54`
**Issue:** Complex fixture relationships not documented
**Fix:** Added ASCII dependency tree diagram in module docstring showing all fixture relationships and notes about naming conventions

#### TOOL-005: Remaining Lines Calculation Off-by-One
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/read.py:180-184`
**Fix:** Changed `total_lines > offset + limit - 1` to `total_lines > offset + limit` and remaining calculation accordingly.

#### TOOL-006: Dry Run Doesn't Validate Paths
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/write.py:79-109`
**Fix:** Added path validation in dry run mode: checks if ancestor directories are writable and if existing file is writable.

#### TOOL-007: GrepTool head_limit=0 Treated as Default
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/grep.py:177-179`
**Fix:** Changed to use `is None` check so `head_limit=0` means unlimited results.

#### TOOL-008: No Timeout in Grep Searches
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/tools/file/grep.py:28, 155-160, 202-220, 243-265`
**Fix:** Added `DEFAULT_TIMEOUT` (60s), timeout parameter, and `_search_files_sync()` helper wrapped with `asyncio.wait_for()`.

#### TOOL-009: Edit Tool Doesn't Preserve File Encoding
**Status:** Deferred
**File:** `src/code_forge/tools/file/edit.py:119-120, 152`
**Issue:** Always uses UTF-8, losing original file encoding (latin-1, utf-16)
**Note:** Requires adding chardet as a dependency. Deferred to future enhancement.

#### TOOL-010: Exception Details Leaked in Error Messages
**Status:** Deferred
**Files:** Multiple tool files
**Issue:** Raw exception strings may leak system information (paths, library versions)
**Note:** Requires systematic audit of all tools. Deferred to future security pass.

#### LLM-010: Parameter Mutation in List Building
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/llm.py:98`
**Fix:** Simplified to `all_stops = list(self.stop or []) + list(stop or [])` on single line.

#### LLM-011: Silent Failure on Missing Content Keys
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/memory.py:127`
**Fix:** Added logging.warning() when content part dict is missing 'text' key, showing available keys.

#### LLM-012: Type Hint Forward Reference Issue
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/langchain/memory.py:41`
**Note:** The file uses `from __future__ import annotations` which makes all annotations strings by default (PEP 563). The TYPE_CHECKING pattern is correct and works properly.

#### LLM-013: O(n) Tool Call Lookup in Streaming
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/llm/streaming.py:63-90`
**Note:** The code uses O(1) list index access (`tool_calls[index]`), not linear search. The list is extended to size as needed, and direct index access is constant time.

#### LLM-014: Thread Overhead Per Call
**Status:** Deferred
**File:** `src/code_forge/langchain/llm.py:246-260`
**Issue:** Creates new thread for every streaming operation
**Note:** Requires design work for module-level thread pool with proper lifecycle management. Deferred to future optimization pass.

#### LLM-015: Unused Token Tracking in Stream
**Status:** Not a bug (2025-12-17)
**File:** `src/code_forge/langchain/agent.py:534-592`
**Note:** Token tracking IS implemented. Lines 587-592 increment counters from usage_metadata, and lines 674-676 use them in the AGENT_END event.

#### LLM-016: Incomplete json_mode Implementation
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/langchain/llm.py:425-430`
**Fix:** Now raises NotImplementedError with clear message explaining to use function_calling method instead.

#### LLM-017: No Pagination in list_models()
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/client.py:250-253`
**Fix:** Added documentation Note in docstring explaining the limitation and suggesting client-side filtering for large model lists.

#### LLM-018: Silent Type Coercion in Content Handling
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/llm/models.py:86-93`
**Fix:** Added logger.warning() for unexpected content types, showing the actual type received.

#### CFG-006: Missing Null Check in EnvironmentSource
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/sources.py:221-274`
**Fix:** Added explicit type key sets (BOOLEAN_KEYS, INTEGER_KEYS, etc.) and debug logging for unknown keys.

#### CFG-007: Inconsistent Error Handling in Observer Notification
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:330-348`
**Fix:** _notify_observers() now returns (success_count, failure_count) tuple and logs observer name on error.

#### CFG-008: Missing Timeout for File Watcher Stop
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:325-355`
**Fix:** stop_watching() now accepts optional timeout parameter (default 10s via WATCHER_STOP_TIMEOUT) and returns bool indicating success.

#### CFG-009: No Configuration Change Diff Detection
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:239-268`
**Fix:** reload() now compares old and new config via model_dump() and skips notification if unchanged. Returns bool.

#### CFG-010: No Mechanism to Unwatch Specific Directories
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/config/loader.py:270-323`
**Fix:** watch() now accepts user=True, project=True parameters for granular control. Returns count of directories watched.

#### SESS-010: Inefficient Truncation Strategy
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/context/strategies.py:315-352`
**Fix:** Replaced id(m) mapping with tuple-based index tracking. Now stores (idx, msg) tuples and sorts by original index.

#### SESS-011: Unnecessary Session Index Saves
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/index.py:340-376`
**Fix:** Added 5-second debounce to save_if_dirty(). Added force_save() for critical operations. Tracks last save time with time.monotonic().

#### SESS-012: Confusing Thinking Mode Toggle UX
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/main.py:200-223`
**Fix:** Added user feedback messages when toggling ("Thinking mode enabled/disabled (Ctrl+T to toggle)"). Improved docstring explaining the wrapper pattern.

#### SESS-013: Poor Error Context on Setup Failure
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/cli/setup.py:23-107`
**Fix:** Added DOCS_URL and OPENROUTER_URL constants. Show OpenRouter link on empty key. Added troubleshooting links on all error paths. Separate PermissionError handling with specific hints.

#### SESS-014: Incomplete Spinner State in Error Cases
**Status:** Already fixed (2025-12-17)
**File:** `src/code_forge/cli/main.py:266-412`
**Note:** Spinners initialized to None before try block (lines 266-268). Cleanup in both except (395-399) and finally (401-412) blocks with try-except wrappers.

#### SESS-015: No Context About Session Recovery
**Status:** Fixed (2025-12-17)
**File:** `src/code_forge/sessions/storage.py:197-240`
**Fix:** load() now has auto_recover parameter (default True). On JSONDecodeError, automatically attempts recover_from_backup(). Logs warning on successful recovery. Improved error message on failure.

#### SESS-016: No Validation of Truncation Results
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/context/manager.py:178-212`
**Fix:** Added post-truncation validation that counts tokens after truncation and logs warning if result exceeds target budget. Also logs warning if truncation fails to reduce messages while over limit.

#### PERM-006: Unvalidated Argument Names in Rules
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/permissions/rules.py:96-105`
**Fix:** Added debug logging when argument name in rule pattern doesn't exist in the tool's arguments. Shows which argument name was expected and what arguments are available.

#### PERM-007: Non-atomic Rule Updates
**Status:** Already fixed (2025-12-18)
**File:** `src/code_forge/permissions/checker.py:157-160`
**Note:** Fixed as part of PERM-003. The `add_session_rule()` method already performs both remove and add within a single `with self._session_lock:` block, making the operation atomic.

#### PERM-008: Ambiguous Argument Parsing
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/commands/parser.py:171-188`
**Fix:** Added support for POSIX `--` separator. After `--`, all remaining tokens are treated as positional arguments regardless of whether they start with `-`.

#### PERM-009: Missing Async Exception Handling in Hooks
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/hooks/executor.py:202-205, 312-316`
**Fix:** Added explicit `asyncio.CancelledError` handling in both `execute_hooks()` and `_execute_hook()`. Ensures processes are killed on cancellation and error is properly propagated.

#### PERM-010: Missing Error Context in Permission Config Loading
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/permissions/config.py:153-162, 185-196`
**Fix:** Separate JSONDecodeError handling to include file path, line number, and column number. Other errors now also include file path in message.

#### PERM-011: Uncaught Subprocess Errors in Hooks
**Status:** Already fixed (2025-12-18)
**File:** `src/code_forge/hooks/executor.py:318-341`
**Note:** Code already catches `OSError` specifically for subprocess errors. The catch-all `Exception` handler uses `logger.exception()` which logs full stack traces for unexpected errors. This is the correct pattern for distinguishing expected from unexpected failures.

#### PERM-012: Silent Regex Pattern Failures
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/permissions/rules.py:60-85`
**Fix:** Added warning logging for all regex rejection cases: exceeds max length, potential ReDoS pattern, and invalid regex syntax. Patterns are truncated in logs for safety.

#### PERM-013: Type Validation Without Coercion
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/commands/base.py:77-98`
**Fix:** Added `convert()` method to `CommandArgument` that converts validated values to proper types (int for INTEGER, bool for BOOLEAN). Command handlers can call this after validation.

#### PERM-014: Inconsistent Timeout Handling in Prompts
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/permissions/prompt.py:116-128`
**Fix:** Added docstring note clarifying that `confirm()` does NOT support timeouts and recommending `confirm_async()` for timeout support.

#### PERM-015: No Rate Limiting on Permission Denials
**Status:** Pending
**File:** `src/code_forge/permissions/`
**Issue:** Repeated bypass attempts have no rate limiting
**Impact:** Potential DoS against permission system
**Fix:** Track failed attempts, add backoff

#### PERM-016: No Hook Error Recovery
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:99-178`
**Issue:** No retry logic for transient hook failures
**Impact:** Permanent operation blocking on transient failure
**Fix:** Add `max_retries` parameter

#### PERM-017: No Dry-Run Mode for Hooks
**Status:** Pending
**File:** `src/code_forge/hooks/`
**Issue:** Hooks execute immediately with no preview option
**Impact:** Users can't see what a hook will do first
**Fix:** Add `dry_run` parameter to execute_hooks()

#### PERM-018: No Hook Working Directory Validation
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/hooks/executor.py:249-272`
**Fix:** Added validation that working directory exists and is actually a directory before executing hook. Returns early with descriptive error if validation fails.

#### MCP-006: Unhandled Message Loop Exception
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/client.py:51-77, 363-390`
**Fix:** Added `on_disconnect` callback parameter to MCPClient. Receive loop now invokes callback when connection is lost unexpectedly, allowing manager to handle reconnection.

#### MCP-007: asyncio.get_event_loop() Usage
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/client.py:332`
**Fix:** Changed `asyncio.get_event_loop()` to `asyncio.get_running_loop()` which is the correct pattern for async functions and avoids deprecation warnings in Python 3.10+.

#### MCP-008: Missing Error Handling in SSE Listen
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/transport/http.py:173-177`
**Fix:** Added try-except around `.decode()` call to catch UnicodeDecodeError. Invalid UTF-8 data is now logged and skipped instead of crashing the listener.

#### MCP-009: Insufficient MCP Tool Name Validation
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/tools.py:112-128`
**Fix:** Added detailed validation for MCP tool name format with specific error messages for: wrong number of parts, wrong prefix, empty server name, empty tool name.

#### MCP-010: Silent Entry Point Loading Failures
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/plugins/loader.py:93-111`
**Fix:** Added explicit validation before split() with specific error messages for: missing colon, empty module name, empty class name. Includes example of correct format in error message.

#### MCP-011: No State Transition Validation in Agents
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/agents/base.py:280-299`
**Fix:** Added state validation in `cancel()` method. Returns False and logs warning if agent is already in terminal state (COMPLETED, FAILED, CANCELLED). Changed return type from None to bool.

#### MCP-012: No Token Usage Tracking from LLM
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/agents/executor.py:272-281`
**Fix:** Added fallback token estimation when `usage_metadata` is not available. Estimates tokens from response content length (~4 chars/token).

#### MCP-013: Missing Tool Execution Metadata
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/agents/executor.py:320-356`
**Fix:** Added `_metadata` field to tool results containing tool_name, success status, duration_ms, and error message (if any) for debugging.

#### MCP-014: No Server Request Handler
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/client.py:57-59, 80-81, 427-444`
**Fix:** Added `on_notification` and `on_server_request` callback parameters to MCPClient. Callbacks are invoked when server sends notifications or requests.

#### MCP-015: No Resource Update Notifications
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/client.py:427-434`
**Note:** Addressed by MCP-014. The `on_notification` callback parameter now allows dispatching notifications to listeners.

#### MCP-016: No Circular Dependency Detection in Skills
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:255-278`
**Issue:** Skills can have circular dependencies via prompt references
**Impact:** Potential infinite loops
**Reason:** Requires building full dependency graph - substantial feature addition

#### MCP-017: No Skill Activation Timeout
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/skills/base.py:287-300`
**Fix:** Added docstring clarifying that activate() is a fast synchronous method and subclasses needing slow init should use lazy initialization or async patterns.

#### MCP-018: No HTTP Transport Proxy Support
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/transport/http.py:22-40, 75-79, 131-135, 176-180`
**Fix:** Added `proxy` parameter to HTTPTransport. Proxy URL is passed to all HTTP requests (POST, GET, SSE).

#### MCP-019: Inefficient Plugin Unregister
**Status:** Deferred
**File:** `src/code_forge/plugins/registry.py:153-168`
**Issue:** Dictionary comprehensions iterate entire collection for each type
**Reason:** Current O(n) per collection is acceptable for typical plugin counts. Reverse indexing adds complexity for marginal gains.

#### MCP-020: Linear Search in Skills Registry
**Status:** Deferred
**File:** `src/code_forge/skills/registry.py:136-150`
**Issue:** `search()` iterates all skills
**Reason:** Linear search is acceptable for typical skill counts. Search indexing would add complexity for marginal gains.

#### MCP-021: Unnecessary Message Copies in Agent
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/agents/base.py:330-341`
**Issue:** `messages` property returns copy; inefficient if called repeatedly
**Fix:** Documented defensive copy behavior in docstring with guidance to cache result in local variable when needed repeatedly

#### MCP-022: Skill Context Copying
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/skills/base.py:367-376`
**Issue:** Returns copy on every call
**Fix:** Documented defensive copy behavior in docstring with guidance to cache result

#### MCP-023: Inefficient MCP Settings Merge
**Status:** Fixed (2025-12-18)
**File:** `src/code_forge/mcp/config.py:276-294`
**Issue:** Compares each field with default values multiple times
**Fix:** Created default instance once before loop and used dataclasses.fields() iteration for maintainability

---

### Feature Requests

#### FEAT-001: Per-Project RAG Support
**Status:** Proposed
**Priority:** High
**Description:** Add Retrieval-Augmented Generation (RAG) support on a per-project basis
**Benefits:**
- Index project-specific documentation, code comments, and patterns
- Semantic search over large codebases beyond context window limits
- Persistent knowledge across sessions
- Custom embeddings for domain-specific terminology
- Better understanding of project architecture and conventions

**Implementation Considerations:**
- Local vector database (ChromaDB, Qdrant, or FAISS)
- Configurable embedding models (local or API-based)
- Automatic indexing on project open/file changes
- Integration with context management system
- Project-specific `.forge/index/` directory for vector storage
- Support for multiple index types (code, docs, comments)

**Potential Components:**
- `src/code_forge/rag/indexer.py` - Code and document indexing
- `src/code_forge/rag/embeddings.py` - Embedding generation
- `src/code_forge/rag/retriever.py` - Semantic search
- `src/code_forge/rag/config.py` - Per-project RAG configuration

---

#### FEAT-002: Specialized Task Agents
**Status:** Proposed
**Priority:** High
**Description:** Create different specialized agents for different tasks instead of one general-purpose agent
**Benefits:**
- Better focused prompts for specific tasks
- Specialized tool access per agent type
- Improved output quality for domain-specific work
- Parallel agent execution for complex workflows

**Proposed Agent Types:**

1. **Code Review Agent**
   - Specialized in analyzing diffs and code changes
   - Security vulnerability detection
   - Code style and best practices checking
   - Performance issue identification

2. **Test Generation Agent**
   - Creates test cases from code
   - Identifies edge cases and boundary conditions
   - Generates unit, integration, and e2e tests
   - Maintains test coverage metrics

3. **Documentation Agent**
   - Extracts and generates documentation
   - Creates README files and API docs
   - Updates docstrings and comments
   - Generates architecture diagrams (mermaid)

4. **Refactoring Agent**
   - Identifies code smells and anti-patterns
   - Suggests and implements refactoring
   - Modernizes legacy code patterns
   - Optimizes performance bottlenecks

5. **Planning Agent**
   - Breaks down complex tasks into steps
   - Creates implementation plans
   - Estimates complexity and dependencies
   - Generates task trees and milestones

6. **Debug Agent**
   - Analyzes error messages and stack traces
   - Identifies root causes
   - Suggests fixes with explanations
   - Creates reproduction steps

**Implementation Considerations:**
- Agent registry with metadata and capabilities
- Agent-specific system prompts and tool restrictions
- Agent orchestration for multi-agent workflows
- Shared context between agents
- Agent selection heuristics based on user intent

**Potential Structure:**
```
src/code_forge/agents/
├── specialized/
│   ├── code_review.py
│   ├── test_generation.py
│   ├── documentation.py
│   ├── refactoring.py
│   ├── planning.py
│   └── debug.py
├── orchestrator.py      # Multi-agent coordination
└── selector.py          # Automatic agent selection
```

---

#### FEAT-003: Agent Workflow System
**Status:** Proposed
**Priority:** Medium
**Description:** Enable chaining multiple specialized agents together for complex workflows
**Example Workflows:**
- "Full PR Review": Planning → Code Review → Test Generation → Documentation
- "Bug Fix": Debug → Code Review → Test Generation
- "Feature Implementation": Planning → Implementation → Test → Documentation

**Features:**
- Workflow definition via YAML or code
- Conditional agent execution based on results
- Parallel agent execution where possible
- Workflow templates for common tasks
- Progress tracking and resumability

---

## Completed Milestones

| Version | Date | Summary |
|---------|------|---------|
| 1.3.0 | 2025-12-17 | Streaming error handling fix |
| 1.2.0 | 2025-12-17 | Setup wizard, security fixes |
| 1.1.0 | 2025-12-09 | All 22 phases complete, production ready |
| 1.0.0 | 2025-12-09 | Initial release |

---

## Issue Counts

| Priority | Count | Description |
|----------|-------|-------------|
| P0 Critical | 0 | All critical issues addressed |
| P1 High | 26 | Architecture and significant functional issues |
| P2 Medium | 42 | Quality improvements and UX enhancements |
| P3 Low | 63 | Minor issues and nice-to-haves |
| Features | 3 | New feature proposals (RAG, Specialized Agents, Workflows) |
| **Total** | **134** | (11 P0 issues fixed/resolved, 131 bugs + 3 features) |

---

## How to Use This File

When starting new work:
1. Pick an item from the backlog (start with P0/P1)
2. Move to "Active Tasks" with your progress
3. Update status as work progresses
4. Move to "Completed Milestones" when released

Format for active tasks:
```
### ISSUE-ID: Title
**Status:** In Progress | Blocked | Done
**Assignee:** (if applicable)
**Branch:** (if applicable)
**Notes:** Progress updates
```
