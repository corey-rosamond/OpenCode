# Test Strategy: CI/CD Pipeline Setup

## Test Approach

CI/CD configuration testing is primarily done through actual workflow execution on GitHub. Local validation provides quick feedback but isn't a full substitute.

## Local Validation

### V-1: YAML Syntax Validation
```bash
#!/bin/bash
# Validate all workflow YAML files

for file in .github/workflows/*.yml; do
    echo "Validating $file..."
    python -c "import yaml; yaml.safe_load(open('$file'))" || exit 1
done
echo "All workflow files are valid YAML"
```

### V-2: Action References Check
```bash
#!/bin/bash
# Check that referenced actions exist and versions are pinned

grep -E "uses: [a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+@" .github/workflows/*.yml | while read line; do
    action=$(echo "$line" | grep -oE "[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+@[a-zA-Z0-9]+")
    echo "Found action: $action"
    # Verify it's pinned to a tag/sha, not branch
    if echo "$action" | grep -qE "@(main|master|dev)$"; then
        echo "WARNING: Action $action uses unpinned branch"
    fi
done
```

### V-3: Local Act Simulation
```bash
# Install act (GitHub Actions local runner)
# https://github.com/nektos/act

# Run test workflow locally
act -j test -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest

# Note: May not perfectly match GitHub environment
```

## GitHub Validation Tests

### G-1: Workflow Trigger Test
1. Create a branch with workflow files
2. Push to branch
3. Verify workflow triggers on push
4. Check workflow appears in Actions tab

### G-2: Pull Request Trigger Test
1. Create PR from test branch to main
2. Verify workflow triggers on PR
3. Check status appears on PR
4. Verify all checks pass

### G-3: Matrix Strategy Test
1. Review workflow run logs
2. Verify Python 3.11 job ran
3. Verify Python 3.12 job ran
4. Compare test results between versions

### G-4: Failure Handling Test
1. Create branch with intentionally failing test
2. Push and trigger workflow
3. Verify workflow reports failure
4. Verify failure is visible on PR

### G-5: Issue Template Test
1. Go to Issues tab in repository
2. Click "New Issue"
3. Verify templates appear in selection
4. Create test issue using template
5. Verify template fields populated

### G-6: PR Template Test
1. Create new pull request
2. Verify description pre-filled with template
3. Verify checkboxes are visible
4. Verify sections are clear

## Integration Tests

### I-1: Full PR Workflow Test
```gherkin
Given a complete PR with all workflow files
When the PR is opened
Then the test workflow should run
And all jobs should pass
And coverage should be uploaded
And PR checks should show green
```

### I-2: Release Workflow Test
```gherkin
Given the release workflow is configured
When a tag "v1.0.0-test" is pushed
Then the release workflow should trigger
And a draft release should be created
Then delete the test tag and release
```

## Verification Checklist

### Workflow Files Exist
- [ ] `.github/workflows/test.yml` exists
- [ ] `.github/workflows/pr-check.yml` exists
- [ ] `.github/workflows/release.yml` exists

### Templates Exist
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md` exists
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` exists
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` exists

### Workflow Functionality
- [ ] Test workflow passes on main
- [ ] PR workflow triggers on pull request
- [ ] All matrix jobs complete
- [ ] Coverage report generated

### Template Functionality
- [ ] Bug report template appears in issue dialog
- [ ] Feature request template appears in issue dialog
- [ ] PR template populates on new PR

## Test Execution Order

1. V-1: YAML syntax validation (local)
2. V-2: Action references check (local)
3. Push to test branch
4. G-1: Workflow trigger test
5. G-2: PR trigger test
6. G-3: Matrix strategy test
7. G-5, G-6: Template tests
8. Merge when all pass

## Success Criteria

- All local validations pass
- Workflow triggers correctly on GitHub
- All jobs pass in workflow run
- Templates appear and work correctly
- No regressions in existing functionality
