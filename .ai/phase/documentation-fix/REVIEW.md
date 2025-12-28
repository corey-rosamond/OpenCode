# Code Review Checklist: Documentation Fix

## Pre-Review Verification

Before requesting review, verify:
- [ ] All automated verifications pass
- [ ] README.md loads correctly in GitHub preview
- [ ] No merge conflicts with main branch

## Review Checklist

### Documentation Quality

#### Package References
- [ ] All `forge.` imports changed to `code_forge.`
- [ ] All `src/forge/` paths changed to `src/code_forge/`
- [ ] No orphaned references to old package name

#### Code Examples
- [ ] All Python code blocks use correct syntax
- [ ] Import statements reference real modules
- [ ] Class/function names match implementation
- [ ] Examples are complete (not truncated)

#### Accuracy
- [ ] Project structure diagram matches reality
- [ ] Version numbers are current
- [ ] URLs and links are valid

### Change Quality

#### Minimal Changes
- [ ] Only package name changes made
- [ ] No unrelated formatting changes
- [ ] Whitespace preserved appropriately

#### Consistency
- [ ] Same formatting style throughout
- [ ] Consistent capitalization of package name
- [ ] Consistent use of code vs inline code formatting

### Commit Quality

#### Message
- [ ] Clear, descriptive commit message
- [ ] References issue/phase ID (DOC-001)
- [ ] Explains what was changed and why

#### Scope
- [ ] Commits are logically organized
- [ ] No unrelated changes bundled

## Review Questions

### For Reviewer to Answer

1. Do all code examples look correct?
2. Is the project structure diagram accurate?
3. Are there any old package references I missed?
4. Do the examples make sense in context?

### Known Issues to Ignore

- None for this phase

## Post-Review Actions

After approval:
1. Squash commits if multiple
2. Update CHANGELOG.md with entry
3. Merge to main
4. Verify README renders correctly on GitHub

## Sign-Off

- [ ] Code reviewed and approved
- [ ] All checklist items verified
- [ ] Ready to merge
