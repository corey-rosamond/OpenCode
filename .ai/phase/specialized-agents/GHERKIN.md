# Specialized Task Agents: Behavior Specifications

**Phase:** specialized-agents
**Created:** 2025-12-21
**Updated:** 2025-12-21

All features specified in Gherkin format for BDD testing.

---

## Feature: Agent Type Registry Extension

### Scenario: All 16 new agent types are registered
Given the AgentTypeRegistry is initialized
When I list all agent types
Then I should see 20 agent types total
And the list should contain all existing types: "explore", "plan", "code-review", "general"
And the list should contain all new coding agents: "test-generation", "documentation", "refactoring", "debug"
And the list should contain all new writing agents: "writing", "communication", "tutorial"
And the list should contain new visual agents: "diagram"
And the list should contain new QA agents: "qa-manual"
And the list should contain new research agents: "research", "log-analysis", "performance-analysis"
And the list should contain new security agents: "security-audit", "dependency-analysis"
And the list should contain new project agents: "migration-planning", "configuration"

### Scenario: No duplicate agent types
Given the AgentTypeRegistry is initialized
When I attempt to register an agent type with an existing name
Then a ValueError should be raised
And the error message should contain "already registered"

---

## Feature 1: Coding Agents

### Scenario: test-generation agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "test-generation"
Then the agent type should exist
And the description should be "Generates test cases for code"
And the default tools should be ["glob", "grep", "read", "write"]
And the max tokens should be 40000
And the max time should be 300 seconds

### Scenario: documentation agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "documentation"
Then the agent type should exist
And the description should be "Creates documentation and docstrings"
And the default tools should be ["glob", "grep", "read", "write"]
And the max tokens should be 35000
And the max time should be 240 seconds

### Scenario: refactoring agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "refactoring"
Then the agent type should exist
And the description should be "Identifies and fixes code smells"
And the default tools should be ["glob", "grep", "read", "write", "edit"]
And the max tokens should be 45000
And the max time should be 360 seconds

### Scenario: debug agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "debug"
Then the agent type should exist
And the description should be "Analyzes errors and suggests fixes"
And the default tools should be ["glob", "grep", "read", "bash"]
And the max tokens should be 30000
And the max time should be 240 seconds

---

## Feature 2: Writing & Communication Agents

### Scenario: writing agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "writing"
Then the agent type should exist
And the description should be "Technical guides, tutorials, blog posts"
And the default tools should be ["read", "write", "web-search", "web-fetch"]
And the max tokens should be 40000
And the max time should be 300 seconds

### Scenario: communication agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "communication"
Then the agent type should exist
And the description should be "PR descriptions, issues, emails"
And the default tools should be ["read", "write", "git", "github"]
And the max tokens should be 25000
And the max time should be 180 seconds

### Scenario: tutorial agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "tutorial"
Then the agent type should exist
And the description should be "Educational content, onboarding materials"
And the default tools should be ["glob", "grep", "read", "write", "web-search"]
And the max tokens should be 45000
And the max time should be 360 seconds

---

## Feature 3: Visual & Design Agents

### Scenario: diagram agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "diagram"
Then the agent type should exist
And the description should be "Mermaid diagrams, architecture visualizations"
And the default tools should be ["glob", "grep", "read", "write"]
And the max tokens should be 30000
And the max time should be 240 seconds

---

## Feature 4: Testing & QA Agents

### Scenario: qa-manual agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "qa-manual"
Then the agent type should exist
And the description should be "Manual testing procedures, QA scenarios"
And the default tools should be ["read", "write", "bash"]
And the max tokens should be 35000
And the max time should be 300 seconds

---

## Feature 5: Research & Analysis Agents

### Scenario: research agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "research"
Then the agent type should exist
And the description should be "Web research, technology evaluation"
And the default tools should be ["web-search", "web-fetch", "read", "write"]
And the max tokens should be 50000
And the max time should be 400 seconds

### Scenario: log-analysis agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "log-analysis"
Then the agent type should exist
And the description should be "Parse and analyze logs for patterns"
And the default tools should be ["read", "grep", "bash", "write"]
And the max tokens should be 40000
And the max time should be 300 seconds

### Scenario: performance-analysis agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "performance-analysis"
Then the agent type should exist
And the description should be "Performance metrics and bottlenecks"
And the default tools should be ["read", "bash", "grep", "write"]
And the max tokens should be 35000
And the max time should be 300 seconds

---

## Feature 6: Security & Dependencies Agents

### Scenario: security-audit agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "security-audit"
Then the agent type should exist
And the description should be "Security-focused code review"
And the default tools should be ["glob", "grep", "read", "bash", "write"]
And the max tokens should be 45000
And the max time should be 360 seconds

### Scenario: dependency-analysis agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "dependency-analysis"
Then the agent type should exist
And the description should be "Dependency health and vulnerabilities"
And the default tools should be ["read", "bash", "web-search", "write"]
And the max tokens should be 35000
And the max time should be 300 seconds

---

## Feature 7: Project Management Agents

### Scenario: migration-planning agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "migration-planning"
Then the agent type should exist
And the description should be "Plan and execute migrations"
And the default tools should be ["glob", "grep", "read", "write", "bash"]
And the max tokens should be 50000
And the max time should be 400 seconds

### Scenario: configuration agent type is properly configured
Given the AgentTypeRegistry is initialized
When I query for agent type "configuration"
Then the agent type should exist
And the description should be "Manage and validate configs"
And the default tools should be ["glob", "read", "write", "edit"]
And the max tokens should be 30000
And the max time should be 240 seconds

---

## Feature 8: Agent Creation and Initialization

### Scenario: Create any agent type successfully
Given I have a valid agent type name
And I have a task description
When I create an agent of that type
Then the agent should be created successfully
And the agent state should be "pending"
And the agent should have the correct tools for its type
And the agent should have the correct resource limits

### Scenario: Agent factory creates correct configuration
Given I want to create a "research" agent
When I call AgentConfig.for_type("research")
Then a config should be returned
And the agent_type should be "research"
And the tools should match research agent requirements
And the max_tokens should be 50000
And the prompt_addition should contain "research agent"

---

## Feature 9: Tool Access Restrictions

### Scenario: test-generation agent can only use allowed tools
Given a test-generation agent
When the agent attempts to use "write" tool
Then the tool execution should succeed
When the agent attempts to use "bash" tool
Then the tool execution should be denied

### Scenario: research agent can use web tools
Given a research agent
When the agent attempts to use "web-search" tool
Then the tool execution should succeed
When the agent attempts to use "web-fetch" tool
Then the tool execution should succeed
When the agent attempts to use "edit" tool
Then the tool execution should be denied

### Scenario: security-audit agent can run bash commands
Given a security-audit agent
When the agent attempts to use "bash" tool
Then the tool execution should succeed

---

## Feature 10: Coding Agent Behaviors

### Scenario: test-generation agent creates comprehensive tests
Given a test-generation agent with task "Generate tests for calculator.py"
And a file "src/calculator.py" with add, subtract, multiply, divide functions
When the agent executes
Then the agent should read "calculator.py"
And the agent should create "tests/test_calculator.py"
And the test file should contain happy path tests
And the test file should contain edge case tests (division by zero)
And the test file should contain boundary tests
And the test file should use pytest
And the agent state should be "completed"

### Scenario: documentation agent generates docstrings
Given a documentation agent with task "Document functions in utils.py"
And a file "src/utils.py" with undocumented functions
When the agent executes
Then the agent should read "src/utils.py"
And the agent should write docstrings in Google style
And each function should document parameters
And each function should document return values
And each function should document exceptions raised
And the agent state should be "completed"

### Scenario: refactoring agent removes code duplication
Given a refactoring agent with task "Remove duplicate code"
And files "a.py" and "b.py" contain duplicate function "calculate_total"
When the agent executes
Then the agent should identify the duplication
And the agent should create a common module
And the agent should use the edit tool to update both files
And both files should import from the common module
And the agent state should be "completed"

### Scenario: debug agent analyzes error and suggests fix
Given a debug agent with task "Fix AttributeError in user.py:42"
And an error message with stack trace
When the agent executes
Then the agent should parse the stack trace
Then the agent should read the source file at line 42
And the agent should identify the root cause
And the agent should suggest a specific fix
And the agent should explain why the error occurred
And the agent state should be "completed"

---

## Feature 11: Writing & Communication Agent Behaviors

### Scenario: writing agent creates technical guide
Given a writing agent with task "Write a guide on adding new tools"
And the agent can read relevant source files
When the agent executes
Then the agent should research the codebase
And the agent should create a structured guide
And the guide should have introduction, steps, and examples
And the guide should be technically accurate
And the agent state should be "completed"

### Scenario: communication agent drafts PR description
Given a communication agent with task "Write PR description for current changes"
And git diff shows changes to authentication module
When the agent executes
Then the agent should read the git diff
And the agent should create a PR description
And the description should summarize the changes
And the description should explain the motivation
And the description should be professionally written
And the agent state should be "completed"

### Scenario: tutorial agent creates step-by-step guide
Given a tutorial agent with task "Create tutorial on using skills"
When the agent executes
Then the agent should read relevant code
And the agent should create a tutorial with numbered steps
And each step should include examples
And the tutorial should assume beginner knowledge
And the tutorial should have clear learning objectives
And the agent state should be "completed"

---

## Feature 12: Visual & Design Agent Behaviors

### Scenario: diagram agent creates architecture diagram
Given a diagram agent with task "Create architecture diagram for the agent system"
When the agent executes
Then the agent should read relevant source files
And the agent should create a Mermaid diagram
And the diagram should show components and relationships
And the diagram should be syntactically valid
And the agent state should be "completed"

### Scenario: diagram agent creates sequence diagram
Given a diagram agent with task "Create sequence diagram for tool execution"
When the agent executes
Then the agent should analyze the code flow
And the agent should create a Mermaid sequence diagram
And the diagram should show the interaction sequence
And the agent state should be "completed"

---

## Feature 13: Testing & QA Agent Behaviors

### Scenario: qa-manual agent creates test procedures
Given a qa-manual agent with task "Create manual test cases for login flow"
When the agent executes
Then the agent should create test scenarios
And each scenario should be in Given/When/Then format
And each scenario should have clear pass/fail criteria
And the scenarios should cover edge cases
And the scenarios should be user-focused
And the agent state should be "completed"

---

## Feature 14: Research & Analysis Agent Behaviors

### Scenario: research agent compares technologies
Given a research agent with task "Compare FastAPI vs Flask for async APIs"
When the agent executes
Then the agent should use web-search to find information
And the agent should use web-fetch to read detailed articles
And the agent should create a comparison report
And the report should list pros and cons
And the report should include sources
And the agent state should be "completed"

### Scenario: log-analysis agent finds error patterns
Given a log-analysis agent with task "Analyze error.log for patterns"
And a file "error.log" with 1000 lines of errors
When the agent executes
Then the agent should read the log file
And the agent should identify recurring errors
And the agent should count error frequencies
And the agent should identify the top 5 errors
And the agent should suggest root causes
And the agent state should be "completed"

### Scenario: performance-analysis agent identifies bottlenecks
Given a performance-analysis agent with task "Find bottlenecks in profiling output"
And a profiling report file exists
When the agent executes
Then the agent should read the profiling data
And the agent should identify slow functions
And the agent should calculate time percentages
And the agent should suggest optimizations
And the agent state should be "completed"

---

## Feature 15: Security & Dependencies Agent Behaviors

### Scenario: security-audit agent finds SQL injection risk
Given a security-audit agent with task "Audit database.py for security issues"
And a file "database.py" with string concatenation in SQL query
When the agent executes
Then the agent should read "database.py"
And the agent should identify the SQL injection risk
And the agent should categorize it as "critical"
And the agent should suggest using parameterized queries
And the agent should explain the vulnerability
And the agent state should be "completed"

### Scenario: security-audit agent checks for OWASP Top 10
Given a security-audit agent with task "Security audit of authentication module"
When the agent executes
Then the agent should check for authentication issues
And the agent should check for sensitive data exposure
And the agent should check for XSS vulnerabilities
And the agent should create a categorized report
And the agent state should be "completed"

### Scenario: dependency-analysis agent finds vulnerabilities
Given a dependency-analysis agent with task "Check dependencies for CVEs"
And a requirements.txt file exists
When the agent executes
Then the agent should read requirements.txt
And the agent should check each package for known CVEs
And the agent should identify outdated packages
And the agent should recommend updates
And the agent state should be "completed"

### Scenario: dependency-analysis agent detects unused dependencies
Given a dependency-analysis agent with task "Find unused dependencies"
When the agent executes
Then the agent should read the dependency list
And the agent should search the codebase for imports
And the agent should identify dependencies not imported anywhere
And the agent should list unused dependencies
And the agent state should be "completed"

---

## Feature 16: Project Management Agent Behaviors

### Scenario: migration-planning agent creates Python upgrade plan
Given a migration-planning agent with task "Plan migration from Python 3.10 to 3.12"
When the agent executes
Then the agent should analyze the current codebase
And the agent should identify Python 3.10-specific features
And the agent should check for deprecated features in 3.12
And the agent should create a step-by-step migration plan
And the plan should include risk assessment
And the agent state should be "completed"

### Scenario: migration-planning agent plans framework migration
Given a migration-planning agent with task "Plan migration from unittest to pytest"
When the agent executes
Then the agent should find all unittest test files
And the agent should analyze test patterns
And the agent should create a conversion strategy
And the strategy should include file-by-file steps
And the agent state should be "completed"

### Scenario: configuration agent validates YAML configs
Given a configuration agent with task "Validate all YAML config files"
And multiple YAML files exist in "config/"
When the agent executes
Then the agent should find all YAML files
And the agent should validate each file for syntax errors
And the agent should report any invalid files
And the agent should suggest fixes
And the agent state should be "completed"

### Scenario: configuration agent compares environments
Given a configuration agent with task "Compare production vs staging configs"
And config files exist for both environments
When the agent executes
Then the agent should read both config files
And the agent should identify differences
And the agent should categorize differences by severity
And the agent should create a comparison report
And the agent state should be "completed"

---

## Feature 17: Resource Management

### Scenario: Agent respects token limits
Given any agent with max_tokens=40000
When the agent execution consumes 40000 tokens
Then the agent execution should stop
And the agent state should be "failed"
And the error should mention "max_tokens exceeded"

### Scenario: Agent respects time limits
Given any agent with max_time_seconds=300
When the agent executes for more than 300 seconds
Then the agent execution should be terminated
And the agent state should be "failed"
And the error should mention "timeout"

### Scenario: Agent tracks resource usage
Given any agent
When the agent executes
Then the usage.tokens_used should be tracked
And the usage.time_seconds should be tracked
And the usage.tool_calls should be tracked
And the usage.iterations should be tracked

---

## Feature 18: Error Handling

### Scenario: Agent handles tool execution errors gracefully
Given any agent
When a tool execution fails with an error
Then the agent should receive the error message
And the agent should handle it gracefully
And the agent should either retry or fail appropriately

### Scenario: Agent handles LLM API errors
Given any agent
When the LLM API returns an error
Then the agent should retry with backoff
And if retries fail the agent state should be "failed"
And the error should be included in the result

### Scenario: Agent handles file not found errors
Given any agent
When the agent tries to read a non-existent file
Then the agent should receive a clear error message
And the agent should handle it appropriately
And the agent should not crash

---

## Feature 19: Integration with Existing Systems

### Scenario: All agents respect permission system
Given any agent type
When the agent attempts to execute a restricted tool
Then the permission system should intercept the request
And the user should be prompted for confirmation
And the agent should respect the permission decision

### Scenario: All agents fire hooks
Given any agent type
And a hook is configured for "tool.before_execute"
When the agent executes a tool
Then the hook should be fired
And the hook should receive correct parameters

### Scenario: All agents work with session system
Given any agent type
When the agent executes
Then the agent's messages should be recorded
And the agent's results should be available
And the session should be persisted

---

## Feature 20: Concurrent Execution

### Scenario: Multiple agents run concurrently without conflicts
Given I create 5 different agents of different types
When I execute all 5 agents concurrently
Then all agents should run independently
And all agents should complete successfully
And there should be no race conditions
And there should be no resource conflicts

### Scenario: Same agent type runs multiple instances
Given I create 3 research agents with different tasks
When I execute all 3 concurrently
Then all 3 should run independently
And all 3 should complete successfully
And their results should be separate

---

## Feature 21: Agent Results

### Scenario: Successful execution produces complete result
Given any agent that completes successfully
When I retrieve the agent result
Then the result should have success=True
And the result should have output text
And the result should have usage statistics
And the result should have execution time
And the result should be serializable to JSON

### Scenario: Failed execution produces error result
Given any agent that fails
When I retrieve the agent result
Then the result should have success=False
And the result should have an error message
And the result should have usage statistics up to failure point
And the result should be serializable to JSON

---

## Feature 22: Agent Cancellation

### Scenario: Running agent can be cancelled
Given any agent that is running
When I call cancel() on the agent
Then the agent state should become "cancelled"
And the agent execution should stop
And the completed_at timestamp should be set
And cancel() should return True

### Scenario: Completed agent cannot be cancelled
Given any agent in "completed" state
When I call cancel() on the agent
Then cancel() should return False
And the agent state should remain "completed"

---

## Feature 23: Agent State Lifecycle

### Scenario: Agent progresses through states correctly
Given a newly created agent
Then the state should be "pending"
When the agent execution starts
Then the state should be "running"
And the started_at timestamp should be set
When the agent completes successfully
Then the state should be "completed"
And the completed_at timestamp should be set
And the result should be available

### Scenario: Agent fails appropriately
Given a running agent
When the agent encounters an unrecoverable error
Then the state should be "failed"
And the completed_at timestamp should be set
And the error should be captured in the result
