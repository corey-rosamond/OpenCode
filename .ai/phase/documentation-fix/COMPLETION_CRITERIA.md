# Completion Criteria: Documentation Fix

## Must Have (Required for Completion)

### CR-1: All Package References Updated
- [ ] Zero occurrences of `from forge.` in README.md
- [ ] Zero occurrences of `import forge.` in README.md
- [ ] Zero occurrences of `src/forge/` in README.md
- [ ] Project structure diagram shows `src/code_forge/`

### CR-2: Code Examples Valid
- [ ] All Python code blocks parse without SyntaxError
- [ ] Import statements reference existing modules
- [ ] Class and function names match actual implementation

### CR-3: Verification Complete
- [ ] `grep -r "from forge\." README.md` returns no results
- [ ] `grep -r "import forge\." README.md` returns no results
- [ ] `grep -r "src/forge/" README.md` returns no results

### CR-4: Other Documentation Checked
- [ ] `docs/` directory audited for old package references
- [ ] Any found occurrences updated

## Should Have (Expected but not blocking)

### CR-5: Example Verification
- [ ] At least 3 code examples tested in actual Python interpreter
- [ ] Tool usage examples verified against actual tool parameters

## Could Have (Nice to have)

### CR-6: Documentation Improvements
- [ ] Add note about package rename history (if helpful for existing users)
- [ ] Verify external links still work

## Won't Have (Explicitly out of scope)

- New documentation sections
- API reference updates
- Tutorial rewrites
- Translation updates

## Definition of Done

This phase is complete when:
1. All CR-1 through CR-4 items are checked
2. Changes committed with descriptive message
3. README examples can be copy-pasted and work
