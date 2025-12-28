# Gherkin Specifications: Code Cleanup

## Feature: ToolCategory Enum Completeness

### Scenario: UTILITY category exists
```gherkin
Given the ToolCategory enum in tools/base.py
When I access ToolCategory.UTILITY
Then the value should be "utility"
And no AttributeError should be raised
```

### Scenario: Test fixtures work with UTILITY
```gherkin
Given the test fixtures in conftest.py
When I run pytest with a test using sample_plugin_dir
Then the EchoTool should have category ToolCategory.UTILITY
And the test should pass without errors
```

### Scenario: All enum values are valid strings
```gherkin
Given the ToolCategory enum
When I iterate over all values
Then each value should be a lowercase string
And each value should be unique
```

## Feature: Dead Code Removal

### Scenario: WebConfig is not imported
```gherkin
Given the code_forge package
When I search for "WebConfig" imports
Then zero files should import WebConfig
Or WebConfig should have a documented reason to exist
```

### Scenario: No broken imports after removal
```gherkin
Given WebConfig has been removed
When I run python -c "import code_forge"
Then no ImportError should be raised
And no AttributeError should be raised
```

## Feature: Single-Source Version

### Scenario: Version comes from package metadata
```gherkin
Given code_forge is installed
When I access code_forge.__version__
Then it should match the version in pyproject.toml
```

### Scenario: Version fallback in development
```gherkin
Given code_forge is not installed (development mode)
When I access code_forge.__version__
Then it should return a fallback version
And no exception should be raised
```

### Scenario: CLI version matches package
```gherkin
Given the forge CLI is available
When I run "forge --version"
Then the output should match code_forge.__version__
```

## Feature: Constants Centralization

### Scenario: Constants module exists
```gherkin
Given the code_forge.core package
When I import from code_forge.core.constants
Then DEFAULT_TIMEOUT should be defined
And MAX_RETRIES should be defined
And no ImportError should be raised
```

### Scenario: Constants are used in code
```gherkin
Given the constants module is created
When I search for hardcoded timeout values
Then at least one file should use constants.DEFAULT_TIMEOUT
```

## Feature: Session Cleanup Command

### Scenario: Cleanup command exists
```gherkin
Given the session commands are registered
When I list available commands
Then "/session cleanup" should be available
```

### Scenario: Cleanup removes old sessions
```gherkin
Given old sessions exist (>30 days old)
When I execute "/session cleanup"
Then old sessions should be deleted
And the response should show count of deleted sessions
```

### Scenario: Cleanup removes old backups
```gherkin
Given old backup files exist
When I execute "/session cleanup"
Then old backups should be deleted
And the response should show count of deleted backups
```

### Scenario: Cleanup with no old sessions
```gherkin
Given no sessions older than 30 days exist
When I execute "/session cleanup"
Then the response should indicate "0 sessions" cleaned
And no error should be raised
```

## Feature: Lock Usage Documentation

### Scenario: All locks are documented
```gherkin
Given files using threading.Lock()
When I read the source code
Then each lock should have a comment explaining its purpose
And the comment should explain why threading.Lock vs asyncio.Lock
```
