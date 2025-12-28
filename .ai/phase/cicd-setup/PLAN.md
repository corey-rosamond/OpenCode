# Phase: CI/CD Pipeline Setup

## Overview

**Phase ID:** CICD-001
**Priority:** Critical (P0)
**Estimated Effort:** 4-6 hours
**Target Version:** 1.8.1

## Problem Statement

The project's test documentation references `.github/workflows/test.yml` but no `.github/` directory exists. This means:
- No automated testing on pull requests
- No quality gates preventing broken code
- No deployment automation
- Claims of CI/CD are false

## Scope

### In Scope
1. Create `.github/workflows/` directory structure
2. Implement test workflow (pytest, mypy, ruff)
3. Implement PR checks workflow
4. Add branch protection recommendations
5. Add release workflow (optional)

### Out of Scope
- Container deployment (Docker, K8s)
- Cloud infrastructure (AWS, GCP)
- PyPI publishing automation (can be added later)
- Dependabot configuration (separate task)

## Implementation Plan

### Step 1: Create Directory Structure
```
.github/
├── workflows/
│   ├── test.yml          # Main test workflow
│   ├── pr-check.yml      # PR validation
│   └── release.yml       # Release automation
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
└── PULL_REQUEST_TEMPLATE.md
```

### Step 2: Test Workflow (test.yml)
Primary workflow for testing on push and PR.

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run linting (ruff)
        run: ruff check src/code_forge/

      - name: Run type checking (mypy)
        run: mypy src/code_forge/

      - name: Run tests
        run: pytest tests/ -v --tb=short

      - name: Run tests with coverage
        run: pytest tests/ --cov=src/code_forge --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false
```

### Step 3: PR Check Workflow (pr-check.yml)
Additional checks specific to pull requests.

```yaml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check PR title format
        run: |
          PR_TITLE="${{ github.event.pull_request.title }}"
          if [[ ! "$PR_TITLE" =~ ^(feat|fix|docs|style|refactor|test|chore)\: ]]; then
            echo "PR title should follow conventional commits format"
            exit 1
          fi

      - name: Check for CHANGELOG update
        run: |
          if git diff --name-only origin/main...HEAD | grep -q "CHANGELOG.md"; then
            echo "CHANGELOG.md has been updated"
          else
            echo "Warning: CHANGELOG.md not updated"
          fi
```

### Step 4: Release Workflow (release.yml)
Automation for creating releases.

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

### Step 5: Issue and PR Templates

**Bug Report Template:**
```markdown
---
name: Bug Report
about: Report a bug or unexpected behavior
labels: bug
---

## Description
[Clear description of the bug]

## Steps to Reproduce
1. ...
2. ...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS:
- Python version:
- Code-Forge version:

## Additional Context
[Screenshots, logs, etc.]
```

**Feature Request Template:**
```markdown
---
name: Feature Request
about: Suggest a new feature
labels: enhancement
---

## Problem
[What problem does this solve?]

## Proposed Solution
[How should it work?]

## Alternatives Considered
[Other approaches you've thought about]

## Additional Context
[Any other information]
```

**PR Template:**
```markdown
## Summary
[Brief description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring
- [ ] Other: ___

## Testing
- [ ] All tests pass locally
- [ ] New tests added for changes
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] CHANGELOG.md updated
```

## Files to Create

| File | Purpose |
|------|---------|
| `.github/workflows/test.yml` | Main test workflow |
| `.github/workflows/pr-check.yml` | PR validation |
| `.github/workflows/release.yml` | Release automation |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Bug report template |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Feature request template |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR template |

## Branch Protection Recommendations

After workflows are set up, configure branch protection for `main`:

1. **Require status checks:**
   - test (Python 3.11)
   - test (Python 3.12)

2. **Require PR reviews:**
   - At least 1 approval

3. **Require up-to-date branches:**
   - Enabled

4. **Restrict pushes:**
   - Only through PRs

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Flaky tests in CI | Medium | Medium | Add retry logic, identify flaky tests |
| Slow CI runs | Medium | Low | Parallelize, cache dependencies |
| Secret exposure | Low | High | Use GitHub secrets, never hardcode |

## Success Metrics

1. All workflows run without errors
2. Tests pass on both Python 3.11 and 3.12
3. Coverage reports generated
4. PR checks enforce quality standards
5. Branch protection enabled on main
