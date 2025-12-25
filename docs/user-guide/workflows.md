# Workflow System

The Code-Forge workflow system enables orchestration of complex multi-step development tasks through coordinated execution of specialized agents. Workflows are defined in YAML and support dependencies, parallel execution, and conditional logic.

## Overview

### What is a Workflow?

A workflow is a directed acyclic graph (DAG) of steps, where each step is executed by a specialized agent. Workflows enable:

- **Multi-step task automation**: Coordinate complex tasks that require multiple agents
- **Parallel execution**: Run independent steps concurrently for faster completion
- **Conditional logic**: Execute steps based on previous step results
- **State persistence**: Checkpoint and resume workflows from failures
- **Template reusability**: Share and reuse workflow definitions

### Key Concepts

- **Workflow**: A collection of steps with dependencies and execution order
- **Step**: A single task executed by an agent (general, explore, plan, etc.)
- **Template**: A reusable workflow definition stored in YAML
- **DAG**: Directed Acyclic Graph - ensures no circular dependencies
- **Checkpoint**: Saved workflow state for resuming after failures

## Using Workflows

### Listing Available Templates

View all available workflow templates:

```bash
/workflow list
```

Search for specific templates:

```bash
/workflow list security    # Find security-related workflows
/workflow list pr          # Find PR-related workflows
```

### Running a Workflow

Execute a workflow template:

```bash
/workflow run pr-review
```

The workflow will execute all steps in dependency order, running independent steps in parallel when possible.

### Monitoring Workflow Status

Check the status of a running workflow:

```bash
/workflow status wf-123abc
```

This displays:
- Current workflow status (running, completed, failed)
- Steps completed, failed, and skipped
- Currently executing step
- Duration and progress

### Resuming Failed Workflows

If a workflow fails, you can resume from the last successful checkpoint:

```bash
/workflow resume wf-123abc
```

This re-runs only the failed step and any dependent steps.

### Canceling Workflows

Stop a running workflow:

```bash
/workflow cancel wf-123abc
```

## Built-in Templates

Code-Forge includes 7 built-in workflow templates:

### 1. PR Review (`pr-review`)

Comprehensive pull request review workflow.

**Steps**:
1. Fetch PR details and files changed
2. Analyze code changes for bugs and issues
3. Check test coverage and test quality
4. Review documentation updates
5. Generate summary report

**Use when**: Reviewing pull requests before merging

### 2. Bug Fix (`bug-fix`)

Systematic bug investigation and fix workflow.

**Steps**:
1. Reproduce the bug
2. Analyze root cause
3. Design fix approach
4. Implement fix
5. Write regression tests
6. Verify fix

**Use when**: Fixing reported bugs systematically

### 3. Feature Implementation (`feature-implementation`)

End-to-end feature development workflow.

**Steps**:
1. Analyze requirements
2. Design architecture
3. Implement core functionality
4. Add tests
5. Update documentation
6. Verify implementation

**Use when**: Implementing new features from requirements

### 4. Security Audit (`security-audit-full`)

Comprehensive security analysis workflow.

**Steps**:
1. Analyze authentication and authorization
2. Check for injection vulnerabilities
3. Review data validation
4. Audit dependency security
5. Check secrets management
6. Generate security report

**Use when**: Performing security audits or pre-release checks

### 5. Code Quality Improvement (`code-quality-improvement`)

Code quality analysis and improvement workflow.

**Steps**:
1. Run static analysis
2. Identify code smells
3. Find refactoring opportunities
4. Check test coverage
5. Generate improvement plan

**Use when**: Improving code quality metrics

### 6. Code Migration (`code-migration`)

Systematic code migration workflow.

**Steps**:
1. Analyze current codebase
2. Plan migration strategy
3. Create compatibility layer
4. Migrate code incrementally
5. Update tests
6. Verify migration

**Use when**: Migrating to new frameworks or patterns

### 7. Parallel Analysis (`parallel-analysis`)

Multi-faceted parallel code analysis.

**Steps**:
- Static analysis (parallel)
- Performance analysis (parallel)
- Security scan (parallel)
- Dependency audit (parallel)
- Aggregate results

**Use when**: Comprehensive codebase analysis

## Creating Custom Workflows

### Workflow Definition Format

Workflows are defined in YAML with the following structure:

```yaml
name: my-workflow
description: Custom workflow description
version: 1.0.0
author: Your Name
metadata:
  category: custom
  tags: [example, tutorial]

steps:
  - id: step1
    agent: general
    description: First step description
    prompt: "Detailed instructions for the agent"
    timeout: 300

  - id: step2
    agent: explore
    description: Second step that depends on first
    prompt: "More instructions"
    depends_on: [step1]
    condition: "step1.success"

  - id: step3
    agent: plan
    description: Parallel step
    depends_on: [step1]
    parallel_with: [step2]
```

### Required Fields

- `name`: Unique identifier for the workflow
- `description`: Human-readable description
- `version`: Semantic version (e.g., "1.0.0")
- `steps`: List of workflow steps

### Step Fields

#### Required
- `id`: Unique step identifier
- `agent`: Agent type (general, explore, plan, etc.)
- `description`: Step description

#### Optional
- `prompt`: Detailed instructions for the agent
- `depends_on`: List of step IDs that must complete first
- `condition`: Boolean expression for conditional execution
- `parallel_with`: List of steps to run in parallel
- `timeout`: Maximum execution time in seconds (default: 300)
- `retry_on_failure`: Whether to retry failed steps (default: false)
- `max_retries`: Maximum retry attempts (default: 3)

### Dependency Rules

1. **No Cycles**: Dependencies must form a DAG (no circular dependencies)
2. **Valid References**: All `depends_on` IDs must exist
3. **Parallel Compatibility**: Parallel steps cannot have interdependencies
4. **Conditional Dependencies**: Conditional steps must depend on the steps they reference

### Template Storage Locations

Templates are discovered in order of precedence:

1. **Project templates**: `.forge/workflows/` in project root (highest priority)
2. **User templates**: `~/.config/code-forge/workflows/`
3. **Built-in templates**: Packaged with Code-Forge (lowest priority)

To override a built-in template, create a template with the same name in a higher-priority location.

### Example: Custom Testing Workflow

```yaml
name: custom-test-workflow
description: Run tests with coverage and quality checks
version: 1.0.0
author: Development Team
metadata:
  category: testing
  tags: [test, qa, coverage]

steps:
  # Run unit tests
  - id: unit_tests
    agent: qa-manual
    description: Execute unit test suite
    prompt: |
      Run all unit tests using pytest.
      Generate coverage report.
      Fail if coverage < 80%.
    timeout: 600
    retry_on_failure: true
    max_retries: 2

  # Run integration tests in parallel
  - id: integration_tests
    agent: qa-manual
    description: Execute integration tests
    prompt: "Run integration tests and verify all pass"
    depends_on: []
    parallel_with: [unit_tests]
    timeout: 900

  # Analyze test quality (depends on both test suites)
  - id: test_quality
    agent: test-generation
    description: Analyze test quality
    prompt: |
      Review test code for:
      - Proper assertions
      - Edge case coverage
      - Test isolation
      Generate improvement suggestions.
    depends_on: [unit_tests, integration_tests]
    condition: "unit_tests.success AND integration_tests.success"

  # Generate report
  - id: report
    agent: documentation
    description: Generate test report
    prompt: "Create comprehensive test report with metrics and recommendations"
    depends_on: [test_quality]
```

Save this as `.forge/workflows/custom-test-workflow.yaml` in your project.

## Advanced Features

### Conditional Execution

Steps can execute conditionally based on previous step results:

```yaml
steps:
  - id: analyze
    agent: explore
    description: Analyze code

  - id: refactor
    agent: refactoring
    description: Refactor if issues found
    depends_on: [analyze]
    condition: "analyze.success AND analyze.issues_found"
```

Condition expressions support:
- Boolean operators: `AND`, `OR`, `NOT`
- Step references: `step_id.success`, `step_id.failed`
- Parentheses for grouping

### Parallel Execution

Independent steps run in parallel automatically. Explicitly declare parallel steps:

```yaml
steps:
  - id: setup
    agent: general
    description: Setup environment

  - id: test_unit
    agent: qa-manual
    description: Run unit tests
    depends_on: [setup]

  - id: test_integration
    agent: qa-manual
    description: Run integration tests
    depends_on: [setup]
    parallel_with: [test_unit]  # Explicitly parallel
```

### Error Handling and Retries

Configure retry behavior for transient failures:

```yaml
steps:
  - id: flaky_step
    agent: general
    description: Step that might fail transiently
    retry_on_failure: true
    max_retries: 3
    timeout: 300
```

### Checkpointing

Workflows automatically checkpoint after each step. If a workflow fails, resume from the last checkpoint:

```bash
/workflow resume wf-123abc
```

This:
1. Loads the saved workflow state
2. Identifies the failed step
3. Re-runs the failed step
4. Continues with dependent steps

## Using Workflows from AI

The AI can discover and execute workflows using the Workflow tool:

```python
# List all workflows
tool.execute(operation="list")

# Search for workflows
tool.execute(operation="search", query="security")

# Get workflow details
tool.execute(operation="info", template_name="pr-review")

# Run a workflow
tool.execute(operation="run", template_name="pr-review")

# Check status
tool.execute(operation="status", workflow_id="wf-123abc")
```

The AI will automatically suggest relevant workflows based on your task.

## Best Practices

### Workflow Design

1. **Keep steps focused**: Each step should have a single, clear responsibility
2. **Use descriptive IDs**: Step IDs should clearly indicate what the step does
3. **Provide detailed prompts**: Give agents clear, specific instructions
4. **Design for failure**: Use retries and conditionals for robust workflows
5. **Leverage parallelism**: Identify independent steps that can run concurrently

### Template Organization

1. **Use semantic versioning**: Increment versions when changing workflows
2. **Document metadata**: Add category and tags for discoverability
3. **Include author information**: Help users understand template provenance
4. **Test before sharing**: Validate workflows work as expected

### Performance Optimization

1. **Minimize dependencies**: Reduce sequential dependencies to enable parallelism
2. **Set appropriate timeouts**: Balance between allowing enough time and failing fast
3. **Use checkpoints wisely**: For long workflows, ensure steps are checkpointable
4. **Profile workflows**: Monitor step durations to identify bottlenecks

### Security Considerations

1. **Validate inputs**: Don't pass untrusted data directly to prompts
2. **Review agent permissions**: Ensure agents have appropriate tool access
3. **Audit workflow changes**: Review workflow modifications before use
4. **Limit workflow scope**: Don't give workflows unnecessary permissions

## Troubleshooting

### Workflow Won't Start

**Problem**: `/workflow run` returns "Template not found"

**Solutions**:
- Verify template name: `/workflow list`
- Check template location: `.forge/workflows/`, `~/.config/code-forge/workflows/`
- Validate YAML syntax: Use a YAML linter

### Workflow Fails Immediately

**Problem**: Workflow fails on first step

**Solutions**:
- Check agent availability: Ensure agent type is valid
- Review step prompt: Ensure instructions are clear
- Check dependencies: Verify all `depends_on` steps exist
- Validate timeout: Increase timeout if step needs more time

### Workflow Hangs

**Problem**: Workflow appears stuck

**Solutions**:
- Check status: `/workflow status wf-id`
- Review logs: Check for agent errors
- Cancel and retry: `/workflow cancel wf-id` then re-run
- Increase timeout: Some steps may need more time

### Cannot Resume Workflow

**Problem**: `/workflow resume` returns error

**Solutions**:
- Verify workflow ID: Use `/workflow status wf-id` to check existence
- Check workflow state: Can only resume FAILED or PAUSED workflows
- Review checkpoint: Ensure checkpoint file exists and is valid

### Circular Dependency Error

**Problem**: "Circular dependency detected" error

**Solutions**:
- Review dependencies: Draw the dependency graph
- Remove cycles: Ensure no step depends on itself (directly or indirectly)
- Validate parallel steps: Parallel steps cannot depend on each other

## Examples

### Example 1: Simple Sequential Workflow

```yaml
name: simple-setup
description: Setup and verify environment
version: 1.0.0

steps:
  - id: install_deps
    agent: general
    description: Install dependencies
    prompt: "Run npm install and verify all packages installed"

  - id: run_tests
    agent: qa-manual
    description: Run tests
    prompt: "Execute test suite and verify all tests pass"
    depends_on: [install_deps]

  - id: build
    agent: general
    description: Build project
    prompt: "Run build command and verify successful compilation"
    depends_on: [run_tests]
```

### Example 2: Parallel Analysis Workflow

```yaml
name: code-analysis
description: Parallel code analysis
version: 1.0.0

steps:
  - id: lint
    agent: general
    description: Run linter
    prompt: "Run ESLint and report issues"

  - id: type_check
    agent: general
    description: Type checking
    prompt: "Run TypeScript type checker"
    parallel_with: [lint]

  - id: security_scan
    agent: security-audit
    description: Security scanning
    prompt: "Run security vulnerability scan"
    parallel_with: [lint, type_check]

  - id: aggregate
    agent: general
    description: Aggregate results
    prompt: "Combine all analysis results into summary report"
    depends_on: [lint, type_check, security_scan]
```

### Example 3: Conditional Workflow

```yaml
name: smart-deploy
description: Deploy with conditional checks
version: 1.0.0

steps:
  - id: run_tests
    agent: qa-manual
    description: Run test suite
    prompt: "Execute all tests"

  - id: build
    agent: general
    description: Build application
    prompt: "Build production bundle"
    depends_on: [run_tests]
    condition: "run_tests.success"

  - id: deploy_staging
    agent: general
    description: Deploy to staging
    prompt: "Deploy to staging environment"
    depends_on: [build]
    condition: "build.success"

  - id: smoke_tests
    agent: qa-manual
    description: Run smoke tests
    prompt: "Execute smoke tests on staging"
    depends_on: [deploy_staging]

  - id: deploy_prod
    agent: general
    description: Deploy to production
    prompt: "Deploy to production environment"
    depends_on: [smoke_tests]
    condition: "smoke_tests.success"
```

## Command Reference

### `/workflow list [query]`

List all available workflow templates, optionally filtered by search query.

**Examples**:
```bash
/workflow list              # List all templates
/workflow list security     # Search for "security"
/workflow list pr           # Search for "pr"
```

### `/workflow run <template_name>`

Execute a workflow template.

**Examples**:
```bash
/workflow run pr-review
/workflow run bug-fix
/workflow run my-custom-workflow
```

**Returns**: Workflow ID for status tracking

### `/workflow status <workflow_id>`

Check the status of a running or completed workflow.

**Examples**:
```bash
/workflow status wf-123abc
```

**Returns**: Current status, progress, step results

### `/workflow resume <workflow_id>`

Resume a failed or paused workflow from the last checkpoint.

**Examples**:
```bash
/workflow resume wf-123abc
```

**Requirements**: Workflow must be in FAILED or PAUSED state

### `/workflow cancel <workflow_id>`

Cancel a running workflow.

**Examples**:
```bash
/workflow cancel wf-123abc
```

**Effect**: Marks workflow as CANCELLED, stops execution

## API Reference

For programmatic access, see the [Workflow API Reference](../reference/workflow-api.md).

## See Also

- [Agent Types](agents.md) - Available agent types for workflow steps
- [Commands Reference](commands.md) - All available commands
- [Configuration](../reference/configuration.md) - Workflow configuration options
- [Architecture](../development/architecture.md) - Workflow system architecture
