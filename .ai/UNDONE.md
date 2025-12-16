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
**Status:** Pending
**File:** `src/code_forge/cli/main.py`
**Issue:** Direct instantiation of ConfigLoader, OpenRouterClient, etc.
**Impact:** Hard to test, difficult to swap implementations
**Fix:** Implement dependency injection pattern

#### ARCH-004: Configuration System Fragmentation
**Status:** Pending
**Files:** `config/`, `mcp/config.py`, `hooks/config.py`, `permissions/config.py`, `web/config.py`
**Issue:** 6+ modules use different config patterns (Pydantic vs dataclass vs custom)
**Impact:** Inconsistent API, hard to compose/test configurations
**Fix:** Standardize on Pydantic models with common base class

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
**Status:** Pending
**File:** `src/code_forge/langchain/tools.py:57-91`
**Issue:** Schema generation only covers basic types (string, int, float, boolean, array, object)
**Impact:** Nested objects, union types, enums, custom types not supported
**Fix:** Use Pydantic's `model_json_schema()` recursively

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
**Status:** Pending
**File:** `src/code_forge/permissions/rules.py:162-164`
**Issue:** Glob pattern matching doesn't account for path traversal evasion
**Impact:** Rule bypass via `/etc/../etc/passwd` style paths
**Fix:** Add path normalization before matching

#### PERM-002: Unvalidated Hook Environment Variables
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:206-207`
**Issue:** Hook env vars merged without validation; can overwrite PATH, LD_PRELOAD
**Impact:** Arbitrary code execution via env var injection
**Fix:** Whitelist safe variables or blacklist dangerous ones

#### PERM-003: Thread-Safety of Session Rules
**Status:** Pending
**File:** `src/code_forge/permissions/checker.py:45-60`
**Issue:** RuleSet has no locking; session_rules can be modified from multiple threads
**Impact:** Inconsistent results or crashes
**Fix:** Add threading.RLock to RuleSet or PermissionChecker

#### PERM-004: HookResult.should_continue Ignores Errors
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:50-56`
**Issue:** Property only checks exit code, ignores `timed_out` and `error` fields
**Impact:** Code continues on timeout/error incorrectly
**Fix:** Return `self.exit_code == 0 and not self.timed_out and not self.error`

#### PERM-005: No Audit Logging for Permission Decisions
**Status:** Pending
**File:** `src/code_forge/permissions/`
**Issue:** Permission checks happen silently with no audit trail
**Impact:** No security record of who ran what with what permissions
**Fix:** Add optional permission audit logging

#### MCP-001: Race Condition in Agent Manager
**Status:** Pending
**File:** `src/code_forge/agents/manager.py:297-302`
**Issue:** `agent_ids` can be modified between getting tasks and waiting
**Impact:** Inconsistent state with concurrent access
**Fix:** Capture all IDs atomically with lock

#### MCP-002: Missing Dependency Validation in Plugins
**Status:** Pending
**File:** `src/code_forge/plugins/manager.py:70-78`
**Issue:** Plugin manifest `dependencies` field never validated or installed
**Impact:** Plugins with missing dependencies fail silently at runtime
**Fix:** Add dependency checking during discovery or before activation

#### MCP-003: Missing Reconnection Logic
**Status:** Pending
**File:** `src/code_forge/mcp/manager.py:276-286`
**Issue:** Config includes `reconnect_attempts` and `reconnect_delay` but they're never used
**Impact:** Connection failures don't trigger automatic reconnection
**Fix:** Implement exponential backoff reconnection

#### MCP-004: Missing Path Traversal Protection in Config Save
**Status:** Pending
**File:** `src/code_forge/mcp/config.py:322`
**Issue:** `save_to_file` doesn't validate path argument
**Impact:** User tricked into saving config to unexpected locations
**Fix:** Restrict paths to specific directories

#### MCP-005: Potential Injection Through Skill Context Values
**Status:** Pending
**File:** `src/code_forge/skills/base.py:342-345`
**Issue:** Regex-based sanitization could be bypassed with careful encoding
**Impact:** Prompt injection through context values
**Fix:** Use Jinja2 templating or add length limits

---

### Low Priority (P3)

#### TEST-001: 555 Weak Assertions
**Status:** Pending
**Location:** Throughout test suite
**Issue:** Heavy use of `assert is not None` instead of specific value checks
**Impact:** Tests may pass when they shouldn't
**Fix:** Replace with specific assertions

#### TEST-002: Only 1 Parametrized Test
**Status:** Pending
**Location:** Tests throughout
**Issue:** Could benefit from `@pytest.mark.parametrize` for variations
**Impact:** Missing edge case coverage
**Fix:** Add parametrization for HTTP codes, error scenarios, file formats

#### TEST-003: No Concurrent/Race Condition Tests
**Status:** Pending
**Location:** Test suite
**Issue:** No tests for simultaneous operations or race conditions
**Impact:** Concurrency bugs may exist
**Fix:** Add tests for parallel tool execution, concurrent sessions

#### TEST-004: providers/ Module Has No Tests
**Status:** Pending
**Location:** `src/code_forge/providers/`
**Issue:** Module exists but has no corresponding tests
**Impact:** Untested code
**Fix:** Add tests or remove placeholder module

#### DOC-001: Fixture Dependency Chains Not Documented
**Status:** Pending
**File:** `tests/conftest.py`
**Issue:** Complex fixture relationships not documented
**Impact:** Hard to understand test setup
**Fix:** Add documentation comments

#### TOOL-005: Remaining Lines Calculation Off-by-One
**Status:** Pending
**File:** `src/code_forge/tools/file/read.py:180-182`
**Issue:** `offset + limit - 1` should be `offset + limit`
**Impact:** Slightly incorrect metadata
**Fix:** Correct the calculation

#### TOOL-006: Dry Run Doesn't Validate Paths
**Status:** Pending
**File:** `src/code_forge/tools/file/write.py:80-88`
**Issue:** Dry run returns success without validating path would work
**Impact:** False positive on invalid paths
**Fix:** Perform validation even in dry run

#### TOOL-007: GrepTool head_limit=0 Treated as Default
**Status:** Pending
**File:** `src/code_forge/tools/file/grep.py:169`
**Issue:** `head_limit=0` falls back to DEFAULT instead of unlimited
**Impact:** Can't explicitly request unlimited results
**Fix:** Use `if head_limit is None:` check

#### TOOL-008: No Timeout in Grep Searches
**Status:** Pending
**File:** `src/code_forge/tools/file/grep.py`
**Issue:** Unlike Bash tool, Grep searches have no timeout
**Impact:** Large codebases with slow regex can hang indefinitely
**Fix:** Add timeout handling via `asyncio.wait_for()`

#### TOOL-009: Edit Tool Doesn't Preserve File Encoding
**Status:** Pending
**File:** `src/code_forge/tools/file/edit.py:119-120, 152`
**Issue:** Always uses UTF-8, losing original file encoding (latin-1, utf-16)
**Impact:** File encoding corruption
**Fix:** Use chardet to detect and preserve original encoding

#### TOOL-010: Exception Details Leaked in Error Messages
**Status:** Pending
**Files:** Multiple tool files
**Issue:** Raw exception strings may leak system information (paths, library versions)
**Impact:** Information disclosure
**Fix:** Sanitize error messages, log full error internally

#### LLM-010: Parameter Mutation in List Building
**Status:** Pending
**File:** `src/code_forge/langchain/llm.py:113`
**Issue:** `all_stops = list(self.stop or []); if stop: all_stops.extend(stop)` pattern confusing
**Impact:** Maintenance confusion
**Fix:** Use clearer approach: `all_stops = (self.stop or []) + (stop or [])`

#### LLM-011: Silent Failure on Missing Content Keys
**Status:** Pending
**File:** `src/code_forge/langchain/memory.py:127`
**Issue:** Content list without "text" keys silently returns empty string
**Impact:** Data loss without warning
**Fix:** Add validation or log warning when content structure unexpected

#### LLM-012: Type Hint Forward Reference Issue
**Status:** Pending
**File:** `src/code_forge/langchain/memory.py:41`
**Issue:** Import is TYPE_CHECKING only but field uses `Message` at runtime
**Impact:** Forward reference issue
**Fix:** Import unconditionally or use string annotation

#### LLM-013: O(n) Tool Call Lookup in Streaming
**Status:** Pending
**File:** `src/code_forge/llm/streaming.py:63-90`
**Issue:** Tool calls accumulated in list, linearly searched by index
**Impact:** Slow with many tool calls
**Fix:** Use dict keyed by index for O(1) lookup

#### LLM-014: Thread Overhead Per Call
**Status:** Pending
**File:** `src/code_forge/langchain/llm.py:246-260`
**Issue:** Creates new thread for every streaming operation
**Impact:** Thread creation overhead on many small operations
**Fix:** Use module-level thread pool

#### LLM-015: Unused Token Tracking in Stream
**Status:** Pending
**File:** `src/code_forge/langchain/agent.py:206`
**Issue:** Token counters in stream() method never incremented; metrics always 0
**Impact:** Inaccurate usage metrics
**Fix:** Implement proper token tracking or remove unused variables

#### LLM-016: Incomplete json_mode Implementation
**Status:** Pending
**File:** `src/code_forge/langchain/llm.py:373-418`
**Issue:** `with_structured_output()` only handles `function_calling`, not `json_mode`
**Impact:** JSON mode enforcement not implemented
**Fix:** Implement JSON mode or raise NotImplementedError

#### LLM-017: No Pagination in list_models()
**Status:** Pending
**File:** `src/code_forge/llm/client.py:214-226`
**Issue:** Returns all models at once without pagination
**Impact:** Memory issues with 1000+ models
**Fix:** Add pagination support or document limitation

#### LLM-018: Silent Type Coercion in Content Handling
**Status:** Pending
**File:** `src/code_forge/llm/models.py:78`
**Issue:** Undefined content types silently converted
**Impact:** Bugs masked
**Fix:** Raise explicit error for unsupported content types

#### CFG-006: Missing Null Check in EnvironmentSource
**Status:** Pending
**File:** `src/code_forge/config/sources.py:221-254`
**Issue:** No validation that config structure matches expectations
**Impact:** Type conversion failures
**Fix:** Add explicit handling for unknown keys

#### CFG-007: Inconsistent Error Handling in Observer Notification
**Status:** Pending
**File:** `src/code_forge/config/loader.py:297-307`
**Issue:** Observer exceptions silently logged but never propagated
**Impact:** System left in inconsistent state
**Fix:** Return boolean success/failure or provide status method

#### CFG-008: Missing Timeout for File Watcher Stop
**Status:** Pending
**File:** `src/code_forge/config/loader.py:267-276`
**Issue:** Hardcoded 5.0 second timeout may be insufficient
**Impact:** Potential hangs on slow systems
**Fix:** Make timeout configurable or increase to 10+ seconds

#### CFG-009: No Configuration Change Diff Detection
**Status:** Pending
**File:** `src/code_forge/config/loader.py:225-241`
**Issue:** Observers notified even if nothing changed
**Impact:** Expensive re-initialization unnecessarily triggered
**Fix:** Compare old and new config; only notify if different

#### CFG-010: No Mechanism to Unwatch Specific Directories
**Status:** Pending
**File:** `src/code_forge/config/loader.py:243-265`
**Issue:** Once watch() called, both directories watched together
**Impact:** No granular control
**Fix:** Add `watch(user=True, project=True)` parameters

#### SESS-010: Inefficient Truncation Strategy
**Status:** Pending
**File:** `src/code_forge/context/strategies.py:334-340`
**Issue:** Uses `id(m)` to map message order; fails after GC or message copy
**Impact:** Incorrect message ordering
**Fix:** Use message indices directly or stable identifier

#### SESS-011: Unnecessary Session Index Saves
**Status:** Pending
**File:** `src/code_forge/sessions/manager.py:209-210`
**Issue:** Calls `save_if_dirty()` after every operation
**Impact:** Frequent disk I/O
**Fix:** Batch index updates and save periodically

#### SESS-012: Confusing Thinking Mode Toggle UX
**Status:** Pending
**File:** `src/code_forge/cli/main.py:183-199`
**Issue:** Thinking toggle replaces function instead of extending; no user feedback
**Impact:** Non-obvious behavior
**Fix:** Use decorator or composition pattern, add feedback message

#### SESS-013: Poor Error Context on Setup Failure
**Status:** Pending
**File:** `src/code_forge/cli/setup.py:61-82`
**Issue:** Empty API key silently accepted after retries; no troubleshooting help
**Impact:** Poor UX
**Fix:** Add link to troubleshooting docs

#### SESS-014: Incomplete Spinner State in Error Cases
**Status:** Pending
**File:** `src/code_forge/cli/main.py:368-372`
**Issue:** Exception after spinner starts may not properly clean up
**Impact:** Visual artifacts
**Fix:** Use try-finally for spinner initialization

#### SESS-015: No Context About Session Recovery
**Status:** Pending
**File:** `src/code_forge/sessions/storage.py:294-315`
**Issue:** `recover_from_backup()` exists but never called automatically
**Impact:** Manual recovery required
**Fix:** Integrate recovery into load() with user notification

#### SESS-016: No Validation of Truncation Results
**Status:** Pending
**File:** `src/code_forge/context/manager.py:178-193`
**Issue:** No verification that truncated result fits the limit
**Impact:** Potential overflow
**Fix:** Add post-truncation validation

#### PERM-006: Unvalidated Argument Names in Rules
**Status:** Pending
**File:** `src/code_forge/permissions/rules.py:113-119`
**Issue:** Argument patterns don't validate if argument name is valid for tool
**Impact:** Ineffective rules created silently
**Fix:** Log warning for unrecognized argument names

#### PERM-007: Non-atomic Rule Updates
**Status:** Pending
**File:** `src/code_forge/permissions/checker.py:102-104`
**Issue:** `remove_rule` then `add_rule` not atomic
**Impact:** Race condition with concurrent calls
**Fix:** Make atomic or document thread-safety guarantees

#### PERM-008: Ambiguous Argument Parsing
**Status:** Pending
**File:** `src/code_forge/commands/parser.py:168-178`
**Issue:** Positional arguments starting with `-` misinterpreted as flags
**Impact:** Parsing errors
**Fix:** Better parsing of `--` separator

#### PERM-009: Missing Async Exception Handling in Hooks
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:180-220`
**Issue:** `CancelledError` not caught explicitly
**Impact:** Potential unhandled exceptions
**Fix:** Add explicit handling for `asyncio.CancelledError`

#### PERM-010: Missing Error Context in Permission Config Loading
**Status:** Pending
**File:** `src/code_forge/permissions/config.py:153-154`
**Issue:** JSON parsing errors don't indicate file or line
**Impact:** Hard to debug config issues
**Fix:** Add file path to error message

#### PERM-011: Uncaught Subprocess Errors in Hooks
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:268-279`
**Issue:** Generic Exception catch-all hides programming errors
**Impact:** Hard to distinguish expected from unexpected failures
**Fix:** Catch specific exceptions, log stack traces for unexpected

#### PERM-012: Silent Regex Pattern Failures
**Status:** Pending
**File:** `src/code_forge/permissions/rules.py:38-46`
**Issue:** Invalid regex patterns return None silently
**Impact:** Users creating bad rules get no feedback
**Fix:** Log warning when regex compilation fails

#### PERM-013: Type Validation Without Coercion
**Status:** Pending
**File:** `src/code_forge/commands/base.py:47-75`
**Issue:** INTEGER and BOOLEAN types validated but not converted
**Impact:** Command code still gets strings
**Fix:** Return converted value or store in ParsedCommand

#### PERM-014: Inconsistent Timeout Handling in Prompts
**Status:** Pending
**File:** `src/code_forge/permissions/prompt.py:136-170`
**Issue:** Sync version has no timeout; `request.timeout` ignored
**Impact:** Potential hangs
**Fix:** Document that sync method ignores timeout

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
**Status:** Pending
**File:** `src/code_forge/hooks/executor.py:202-203`
**Issue:** Hook working_dir used without validation
**Impact:** Execution in sensitive directories
**Fix:** Validate exists and is directory

#### MCP-006: Unhandled Message Loop Exception
**Status:** Pending
**File:** `src/code_forge/mcp/client.py:371`
**Issue:** Receive loop catches all exceptions without reconnection or notification
**Impact:** Unexpected disconnections unnoticed
**Fix:** Add callback to notify manager for reconnection

#### MCP-007: asyncio.get_event_loop() Usage
**Status:** Pending
**File:** `src/code_forge/mcp/client.py:327`
**Issue:** May not work correctly with multiple event loops
**Impact:** Runtime errors in some async contexts
**Fix:** Use `asyncio.get_running_loop()` instead

#### MCP-008: Missing Error Handling in SSE Listen
**Status:** Pending
**File:** `src/code_forge/mcp/transport/http.py:169`
**Issue:** SSE listener doesn't handle chunk decode errors
**Impact:** Binary data in SSE causes exceptions
**Fix:** Add try-except around line.decode() call

#### MCP-009: Insufficient MCP Tool Name Validation
**Status:** Pending
**File:** `src/code_forge/mcp/tools.py:113-115`
**Issue:** Simple split without edge case checking
**Impact:** Tool name confusion
**Fix:** Add stricter validation or use regex pattern

#### MCP-010: Silent Entry Point Loading Failures
**Status:** Pending
**File:** `src/code_forge/plugins/manifest.py:141-145`
**Issue:** ValueError from split() caught with unclear error message
**Impact:** Hard to diagnose entry point format issues
**Fix:** Provide specific error messages about format requirements

#### MCP-011: No State Transition Validation in Agents
**Status:** Pending
**File:** `src/code_forge/agents/base.py:277-283`
**Issue:** Can cancel a completed agent
**Impact:** Confusing state
**Fix:** Add state machine validation

#### MCP-012: No Token Usage Tracking from LLM
**Status:** Pending
**File:** `src/code_forge/agents/executor.py:272-275`
**Issue:** Token usage only captured if LLM includes `usage_metadata`
**Impact:** Missing metrics for some providers
**Fix:** Add fallback estimation based on prompt/response length

#### MCP-013: Missing Tool Execution Metadata
**Status:** Pending
**File:** `src/code_forge/agents/executor.py:320-327`
**Issue:** Tool execution results don't include timing or status codes
**Impact:** Hard to debug
**Fix:** Wrap execution to capture timing and success/failure

#### MCP-014: No Server Request Handler
**Status:** Pending
**File:** `src/code_forge/mcp/client.py:409-412`
**Issue:** Server requests acknowledged but not handled
**Impact:** MCP spec not fully implemented
**Fix:** Implement request handler callback system

#### MCP-015: No Resource Update Notifications
**Status:** Pending
**File:** `src/code_forge/mcp/client.py:407`
**Issue:** Notifications logged but not dispatched to listeners
**Impact:** Resource changes not propagated
**Fix:** Implement notification dispatcher

#### MCP-016: No Circular Dependency Detection in Skills
**Status:** Pending
**File:** `src/code_forge/skills/registry.py:255-278`
**Issue:** Skills can have circular dependencies via prompt references
**Impact:** Potential infinite loops
**Fix:** Build dependency graph, detect cycles

#### MCP-017: No Skill Activation Timeout
**Status:** Pending
**File:** `src/code_forge/skills/base.py:287-311`
**Issue:** Slow activate method blocks entire system
**Impact:** Hangs
**Fix:** Add optional timeout parameter with default

#### MCP-018: No HTTP Transport Proxy Support
**Status:** Pending
**File:** `src/code_forge/mcp/transport/http.py:59-63`
**Issue:** aiohttp ClientSession created without proxy configuration
**Impact:** Can't use behind proxy
**Fix:** Add proxy parameter to HTTPTransport

#### MCP-019: Inefficient Plugin Unregister
**Status:** Pending
**File:** `src/code_forge/plugins/registry.py:153-168`
**Issue:** Dictionary comprehensions iterate entire collection for each type
**Impact:** O(n*m) complexity with many plugins
**Fix:** Maintain reverse index mapping plugin_id -> items

#### MCP-020: Linear Search in Skills Registry
**Status:** Pending
**File:** `src/code_forge/skills/registry.py:136-150`
**Issue:** `search()` iterates all skills
**Impact:** Slow with hundreds of skills
**Fix:** Build search index or cache results

#### MCP-021: Unnecessary Message Copies in Agent
**Status:** Pending
**File:** `src/code_forge/agents/base.py:316`
**Issue:** `messages` property returns copy; inefficient if called repeatedly
**Impact:** Performance overhead
**Fix:** Document in docstring, consider read-only wrapper

#### MCP-022: Skill Context Copying
**Status:** Pending
**File:** `src/code_forge/skills/base.py:356`
**Issue:** Returns copy on every call
**Impact:** Inefficient if called frequently
**Fix:** Document behavior in docstring

#### MCP-023: Inefficient MCP Settings Merge
**Status:** Pending
**File:** `src/code_forge/mcp/config.py:283-292`
**Issue:** Compares each field with default values multiple times
**Impact:** Unnecessary computation
**Fix:** Use dataclasses.fields() iteration

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
