# Workflow Examples

This directory contains example workflow templates that demonstrate various workflow patterns and use cases.

## Using These Examples

1. **Copy to your project**:
   ```bash
   cp examples/workflows/my-workflow.yaml .forge/workflows/
   ```

2. **Copy to user templates**:
   ```bash
   cp examples/workflows/my-workflow.yaml ~/.config/code-forge/workflows/
   ```

3. **Customize for your needs**:
   - Edit step prompts to match your project structure
   - Adjust agent types based on your requirements
   - Modify dependencies and parallelism
   - Set appropriate timeouts

## Available Examples

### `ci-pipeline.yaml`
A complete CI/CD pipeline workflow that runs tests, builds, and deploys.

**Use case**: Automating continuous integration and deployment

**Key features**:
- Parallel test execution (unit, integration, e2e)
- Conditional deployment based on test results
- Multi-stage deployment (staging → production)

### `code-review.yaml`
Comprehensive code review workflow for reviewing code changes.

**Use case**: Automated code review assistance

**Key features**:
- Static analysis and linting
- Security vulnerability scanning
- Documentation quality check
- Test coverage analysis

### `api-development.yaml`
End-to-end API development workflow.

**Use case**: Developing new API endpoints

**Key features**:
- Requirement analysis
- API design and specification
- Implementation and testing
- Documentation generation

### `refactoring-workflow.yaml`
Systematic code refactoring workflow.

**Use case**: Large-scale code refactoring projects

**Key features**:
- Code smell detection
- Refactoring strategy planning
- Incremental refactoring with tests
- Validation and rollback safety

### `data-migration.yaml`
Database migration workflow with safety checks.

**Use case**: Database schema or data migrations

**Key features**:
- Backup verification
- Migration script validation
- Rollback plan creation
- Post-migration verification

## Workflow Patterns

### Sequential Pattern
Steps execute one after another in strict order:
```yaml
steps:
  - id: step1
  - id: step2
    depends_on: [step1]
  - id: step3
    depends_on: [step2]
```

### Parallel Pattern
Independent steps execute concurrently:
```yaml
steps:
  - id: step1
  - id: step2
    parallel_with: [step1]
  - id: step3
    parallel_with: [step1, step2]
```

### Fan-Out/Fan-In Pattern
Parallel execution followed by aggregation:
```yaml
steps:
  - id: split
  - id: process_a
    depends_on: [split]
  - id: process_b
    depends_on: [split]
    parallel_with: [process_a]
  - id: merge
    depends_on: [process_a, process_b]
```

### Conditional Pattern
Steps execute based on conditions:
```yaml
steps:
  - id: analyze
  - id: fix
    depends_on: [analyze]
    condition: "analyze.success AND analyze.issues_found"
  - id: verify
    depends_on: [analyze, fix]
    condition: "fix.success OR NOT analyze.issues_found"
```

## Customization Tips

1. **Adjust agent types**: Choose the most appropriate agent for each task
2. **Set realistic timeouts**: Consider complexity and expected duration
3. **Add retry logic**: For flaky operations (network calls, external services)
4. **Use clear prompts**: Provide specific, actionable instructions to agents
5. **Design for resumability**: Ensure steps can be resumed after failures
6. **Document assumptions**: Add comments about expected project structure

## Contributing Examples

Have a useful workflow pattern? Consider contributing it:

1. Ensure the workflow follows best practices
2. Test the workflow in a real project
3. Document the use case and key features
4. Add clear comments and descriptive prompts
5. Submit a pull request

## See Also

- [Workflow User Guide](../../docs/user-guide/workflows.md) - Complete workflow documentation
- [Built-in Templates](../../src/code_forge/workflows/templates/) - Production-ready templates
- [Agent Types](../../docs/user-guide/agents.md) - Available agent types
