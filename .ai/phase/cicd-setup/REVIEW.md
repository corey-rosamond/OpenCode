# Code Review Checklist: CI/CD Pipeline Setup

## Pre-Review Verification

Before requesting review, verify:
- [ ] All YAML files pass syntax validation
- [ ] Workflow triggered successfully on test branch
- [ ] All jobs passed in test run
- [ ] No secrets accidentally committed

## Review Checklist

### Workflow Structure

#### test.yml
- [ ] Name is descriptive ("Tests")
- [ ] Triggers on push to main
- [ ] Triggers on pull_request to main
- [ ] Uses matrix for Python versions
- [ ] Jobs have clear names

#### Steps Quality
- [ ] actions/checkout@v4 (or later)
- [ ] actions/setup-python@v5 (or later)
- [ ] Versions are pinned to tags, not branches
- [ ] Steps have descriptive names

#### Job Configuration
- [ ] runs-on: ubuntu-latest (or pinned version)
- [ ] Python versions include 3.11, 3.12
- [ ] fail-fast set appropriately

### Test Execution

#### Commands Correct
- [ ] pip install command includes dev dependencies
- [ ] ruff check command matches local usage
- [ ] mypy command matches local usage
- [ ] pytest command runs correct test directory

#### Coverage
- [ ] Coverage report generated
- [ ] Coverage artifact uploaded
- [ ] Coverage failure doesn't break workflow (optional)

### PR Checks

#### pr-check.yml
- [ ] Triggers on correct events
- [ ] Title validation is not overly strict
- [ ] CHANGELOG check is warning only
- [ ] Doesn't duplicate test workflow

### Templates

#### Issue Templates
- [ ] Bug report has required sections
- [ ] Feature request has required sections
- [ ] Labels are appropriate
- [ ] Clear instructions for users

#### PR Template
- [ ] Summary section
- [ ] Type of change checkboxes
- [ ] Testing checkboxes
- [ ] Checklist items are relevant

### Security

#### Secrets
- [ ] No hardcoded secrets
- [ ] No API keys in workflow files
- [ ] Secrets referenced via ${{ secrets.NAME }}

#### Permissions
- [ ] Minimal permissions used
- [ ] No write access unless needed
- [ ] No dangerous actions

### Performance

#### Caching
- [ ] pip cache considered
- [ ] Cache key includes Python version
- [ ] Cache restored before install

#### Efficiency
- [ ] No duplicate work between jobs
- [ ] Parallel execution where possible
- [ ] Reasonable timeouts set

## Documentation

### Updates Required
- [ ] tests/README.md updated
- [ ] CHANGELOG.md entry added
- [ ] README badges added (if using)

### Accuracy
- [ ] Workflow descriptions match behavior
- [ ] Commands match what workflow does
- [ ] No references to non-existent workflows

## Testing Evidence

### Workflow Runs
- [ ] Link to successful workflow run provided
- [ ] All matrix jobs visible
- [ ] No warnings or errors

### Template Testing
- [ ] Screenshot of issue template selection
- [ ] Screenshot of PR template populated

## Review Questions

### For Reviewer

1. Are the trigger conditions appropriate?
2. Are all necessary checks included?
3. Is the matrix strategy sufficient?
4. Are templates user-friendly?
5. Any security concerns?

### Known Issues to Ignore

- codecov token may not be configured yet
- Branch protection not yet enabled
- Release workflow not yet tested with real tag

## Post-Review Actions

After approval:
1. Merge workflow files to main
2. Verify workflow triggers on merge
3. Enable branch protection (optional)
4. Configure codecov if desired
5. Update UNDONE.md

## Sign-Off

- [ ] Workflow files reviewed
- [ ] Templates reviewed
- [ ] Security verified
- [ ] Ready to merge
