# TEST-002: Parametrized Tests Implementation

## Summary

Successfully implemented 15+ new parametrized tests throughout the test suite using `@pytest.mark.parametrize`. These tests significantly improve test coverage by testing multiple scenarios with the same test logic, reducing code duplication and making the test suite more maintainable.

## Added Parametrized Tests

### 1. File Tools - test_read.py (3 parametrized tests)

#### TestReadToolErrorHandling.test_relative_path_rejected
- **Location**: `/tests/unit/tools/file/test_read.py:174-192`
- **Purpose**: Tests rejection of relative paths
- **Parameters**: 4 different relative path patterns
- **Values**:
  - `relative/path.txt`
  - `../parent/file.txt`
  - `./current/file.py`
  - `file.json`

#### TestReadToolSecurityValidation.test_path_traversal_rejected
- **Location**: `/tests/unit/tools/file/test_read.py:296-315`
- **Purpose**: Tests path traversal attack prevention
- **Parameters**: 4 malicious path patterns
- **Values**:
  - `../../../etc/passwd`
  - `/../../../etc/shadow`
  - `/./../../etc/hosts`
  - `/../../../../../root/.ssh/id_rsa`

#### TestReadToolFileExtensions.test_read_various_file_types
- **Location**: `/tests/unit/tools/file/test_read.py:318-344`
- **Purpose**: Tests reading different file types/extensions
- **Parameters**: 8 file extension + content pairs
- **Values**: `.txt`, `.py`, `.js`, `.json`, `.md`, `.yaml`, `.xml`, `.csv`

---

### 2. File Tools - test_edit.py (4 parametrized tests)

#### TestEditToolErrorHandling.test_file_not_found
- **Location**: `/tests/unit/tools/file/test_edit.py:213-233`
- **Purpose**: Tests error handling for missing files
- **Parameters**: 3 file scenarios with expected error messages
- **Values**: `nonexistent.txt`, `missing_file.py`, `absent.json`

#### TestEditToolErrorHandling.test_old_string_not_found
- **Location**: `/tests/unit/tools/file/test_edit.py:235-256`
- **Purpose**: Tests error when search string doesn't exist
- **Parameters**: 4 different non-existent strings
- **Values**: Various non-matching search patterns

#### TestEditToolErrorHandling.test_same_old_and_new_string
- **Location**: `/tests/unit/tools/file/test_edit.py:258-278`
- **Purpose**: Tests validation that old and new strings must differ
- **Parameters**: 3 identical string values
- **Values**: `hello`, `world`, `same text`

#### TestEditToolErrorHandling.test_relative_path_rejected
- **Location**: `/tests/unit/tools/file/test_edit.py:280-301`
- **Purpose**: Tests rejection of relative paths
- **Parameters**: 4 relative path patterns
- **Values**: Various relative path formats

---

### 3. File Tools - test_grep.py (3 parametrized tests)

#### TestGrepToolFileFiltering.test_glob_filter
- **Location**: `/tests/unit/tools/file/test_grep.py:261-283`
- **Purpose**: Tests file filtering with glob patterns
- **Parameters**: 4 glob patterns with expected/excluded files
- **Values**: `*.js`, `*.py`, `*.json`, `src/*.py`

#### TestGrepToolFileFiltering.test_type_filter
- **Location**: `/tests/unit/tools/file/test_grep.py:285-305`
- **Purpose**: Tests filtering by file type
- **Parameters**: 3 file type + pattern + expected file tuples
- **Values**: `py`, `js`, `json` types

#### TestGrepToolOutputModes.test_output_modes
- **Location**: `/tests/unit/tools/file/test_grep.py:420-443`
- **Purpose**: Tests different output mode formats
- **Parameters**: 3 output modes with expected content
- **Values**: `files_with_matches`, `content`, `count`

---

### 4. File Tools - test_write.py (3 parametrized tests)

#### TestWriteToolErrorHandling.test_relative_path_rejected
- **Location**: `/tests/unit/tools/file/test_write.py:179-197`
- **Purpose**: Tests rejection of relative paths
- **Parameters**: 4 relative path patterns
- **Values**: Various relative path formats

#### TestWriteToolSecurityValidation.test_path_traversal_rejected
- **Location**: `/tests/unit/tools/file/test_write.py:254-275`
- **Purpose**: Tests path traversal attack prevention
- **Parameters**: 4 malicious path patterns
- **Values**: Including attempts to write to `/etc/passwd`, `/etc/shadow`, etc.

#### TestWriteToolFileExtensions.test_write_various_file_types
- **Location**: `/tests/unit/tools/file/test_write.py:278-304`
- **Purpose**: Tests writing different file types
- **Parameters**: 8 file extension + content pairs
- **Values**: Same as test_read.py - `.txt`, `.py`, `.js`, `.json`, `.md`, `.yaml`, `.xml`, `.csv`

---

### 5. File Tools - test_glob.py (3 parametrized tests)

#### TestGlobToolBasicPatterns.test_glob_patterns
- **Location**: `/tests/unit/tools/file/test_glob.py:68-89`
- **Purpose**: Tests various glob pattern matching
- **Parameters**: 5 pattern + expected files + count tuples
- **Values**: `**/*.py`, `src/*.py`, `**/README.md`, `**/*.json`, `**/*.md`

#### TestGlobToolDefaultExcludes.test_excluded_directories
- **Location**: `/tests/unit/tools/file/test_glob.py:95-127`
- **Purpose**: Tests exclusion of common directories
- **Parameters**: 4 exclude patterns with file locations
- **Values**: `node_modules`, `.venv`, `.git`, `__pycache__`

#### TestGlobToolDefaultExcludes.test_exclude_compiled_files
- **Location**: `/tests/unit/tools/file/test_glob.py:129-145`
- **Purpose**: Tests exclusion of compiled file extensions
- **Parameters**: 4 compiled file extensions
- **Values**: `.pyc`, `.pyo`, `.so`, `.dylib`

---

### 6. Web - test_fetch.py (3 parametrized tests)

#### TestURLFetcher.test_fetch_timeout
- **Location**: `/tests/web/test_fetch.py:145-162`
- **Purpose**: Tests timeout error handling with various messages
- **Parameters**: 3 error type + message + expected match tuples
- **Values**: Different timeout scenarios

#### TestURLFetcher.test_fetch_network_error
- **Location**: `/tests/web/test_fetch.py:164-182`
- **Purpose**: Tests network error scenarios
- **Parameters**: 4 different network error messages
- **Values**: `connection failed`, `network unreachable`, `host not found`, `connection refused`

#### TestURLFetcherStatusCodes.test_successful_status_codes
- **Location**: `/tests/web/test_fetch.py:259-300`
- **Purpose**: Tests handling of different HTTP status codes
- **Parameters**: 6 HTTP status codes
- **Values**: `200`, `201`, `204`, `301`, `302`, `304`

---

### 7. LLM - test_errors.py (3 parametrized tests)

#### TestErrorHierarchy.test_all_errors_catchable_as_llm_error
- **Location**: `/tests/unit/llm/test_errors.py:139-152`
- **Purpose**: Tests all LLM errors inherit from LLMError
- **Parameters**: 6 error class + args pairs
- **Values**: All LLM error types (AuthenticationError, RateLimitError, etc.)

#### TestErrorHierarchy.test_all_errors_catchable_as_forge_error
- **Location**: `/tests/unit/llm/test_errors.py:154-167`
- **Purpose**: Tests all LLM errors inherit from CodeForgeError
- **Parameters**: 6 error class + args pairs
- **Values**: All LLM error types

#### TestLLMErrorMessages.test_custom_error_messages
- **Location**: `/tests/unit/llm/test_errors.py:170-189`
- **Purpose**: Tests custom error messages for each error type
- **Parameters**: 6 error class + message + expected substring tuples
- **Values**: Different error messages for each LLM error type

---

### 8. LLM - test_models.py (3 parametrized tests)

#### TestMessageRole.test_role_values
- **Location**: `/tests/unit/llm/test_models.py:23-33`
- **Purpose**: Tests all message role enum values
- **Parameters**: 4 role + expected value pairs
- **Values**: `SYSTEM`, `USER`, `ASSISTANT`, `TOOL`

#### TestMessage.test_message_factories
- **Location**: `/tests/unit/llm/test_models.py:86-97`
- **Purpose**: Tests message factory methods
- **Parameters**: 3 factory method + content + role tuples
- **Values**: `Message.system`, `Message.user`, `Message.assistant`

#### TestStreamChunk.test_from_dict_with_finish_reason
- **Location**: `/tests/unit/llm/test_models.py:367-383`
- **Purpose**: Tests different finish reasons in stream chunks
- **Parameters**: 4 finish reason values
- **Values**: `stop`, `length`, `tool_calls`, `content_filter`

#### TestCompletionRequestParameters.test_request_with_sampling_params
- **Location**: `/tests/unit/llm/test_models.py:403-427`
- **Purpose**: Tests completion requests with different sampling parameters
- **Parameters**: 5 temperature + max_tokens + top_p tuples
- **Values**: Various combinations of sampling parameters

---

### 9. Permissions - test_rules.py (7 parametrized tests)

#### TestPatternMatcherToolPatterns.test_exact_tool_match
- **Location**: `/tests/unit/permissions/test_rules.py:18-29`
- **Purpose**: Tests exact tool name pattern matching
- **Parameters**: 4 pattern + tool + expected tuples
- **Values**: Various exact tool name matches

#### TestPatternMatcherToolPatterns.test_exact_tool_no_match
- **Location**: `/tests/unit/permissions/test_rules.py:31-42`
- **Purpose**: Tests exact tool name non-matches
- **Parameters**: 4 pattern + tool + expected tuples
- **Values**: Various tool name mismatches

#### TestPatternMatcherToolPatterns.test_glob_tool_match_star
- **Location**: `/tests/unit/permissions/test_rules.py:44-57`
- **Purpose**: Tests wildcard (*) glob patterns
- **Parameters**: 6 pattern + tool + expected tuples
- **Values**: Various wildcard patterns

#### TestPatternMatcherToolPatterns.test_glob_tool_match_question
- **Location**: `/tests/unit/permissions/test_rules.py:59-71`
- **Purpose**: Tests single-char (?) wildcard patterns
- **Parameters**: 5 pattern + tool + expected tuples
- **Values**: Various single-char wildcard patterns

#### TestPatternMatcherToolPatterns.test_implicit_tool_pattern
- **Location**: `/tests/unit/permissions/test_rules.py:73-84`
- **Purpose**: Tests implicit tool patterns (without "tool:" prefix)
- **Parameters**: 4 pattern + tool + expected tuples
- **Values**: Various implicit patterns

#### TestPatternMatcherRegexPatterns.test_regex_starts_with_caret
- **Location**: `/tests/unit/permissions/test_rules.py:136-147`
- **Purpose**: Tests regex patterns starting with ^
- **Parameters**: 4 pattern + tool + args + expected tuples
- **Values**: Path patterns with ^ anchor

#### TestPatternMatcherRegexPatterns.test_regex_ends_with_dollar
- **Location**: `/tests/unit/permissions/test_rules.py:149-160`
- **Purpose**: Tests regex patterns ending with $
- **Parameters**: 4 pattern + tool + args + expected tuples
- **Values**: File extension patterns with $ anchor

#### TestPatternMatcherRegexPatterns.test_regex_with_alternation
- **Location**: `/tests/unit/permissions/test_rules.py:162-174`
- **Purpose**: Tests regex alternation (|) patterns
- **Parameters**: 5 pattern + tool + args + expected tuples
- **Values**: Command patterns with alternation

#### TestPatternMatcherRegexPatterns.test_invalid_regex_returns_false
- **Location**: `/tests/unit/permissions/test_rules.py:176-186`
- **Purpose**: Tests invalid regex handling
- **Parameters**: 3 invalid regex patterns
- **Values**: Various malformed regex patterns

---

## Benefits of Parametrization

1. **Reduced Code Duplication**: Instead of 40+ individual test methods, we have ~35 parametrized tests covering the same scenarios
2. **Better Maintainability**: Changes to test logic only need to be made in one place
3. **Clearer Test Intent**: The parameter values make it obvious what scenarios are being tested
4. **Easy to Extend**: Adding new test cases is as simple as adding a new value to the parameter list
5. **Better Test Organization**: Related test scenarios are grouped together

## Coverage Areas

The parametrized tests cover:

- **HTTP Status Codes**: 200, 201, 204, 301, 302, 304 (6 status codes)
- **Error Scenarios**: Network errors, timeouts, file not found, permission denied, etc.
- **File Formats**: .txt, .py, .js, .json, .md, .yaml, .xml, .csv (8 formats)
- **Input Variations**: Relative paths, absolute paths, malicious paths
- **Edge Cases**: Empty files, unicode content, path traversal attempts
- **Pattern Matching**: Exact, glob, regex patterns for permissions
- **Message Types**: All 4 message roles (system, user, assistant, tool)
- **Error Types**: All 6 LLM error classes

## Statistics

- **Total Parametrized Tests Added**: 35+
- **Total Test Cases Generated**: 150+ (when all parameters are expanded)
- **Files Modified**: 9 test files
- **Test Categories Covered**: 5 (File Tools, Web, LLM, Permissions, Models)

## Running the Tests

All tests use standard pytest parametrize syntax:

```bash
# Run all parametrized tests
pytest tests/ -k "test_" -v

# Run specific test file with parametrization
pytest tests/unit/tools/file/test_read.py -v

# Run specific parametrized test
pytest tests/unit/tools/file/test_read.py::TestReadToolFileExtensions::test_read_various_file_types -v
```

## Notes

- All parametrized tests follow pytest best practices
- Test names are descriptive and indicate what's being tested
- Parameter values are chosen to cover common cases and edge cases
- Tests are organized into logical test classes
- Each test is independent and can run in isolation
