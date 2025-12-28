# Phase: Documentation Fix

## Overview

**Phase ID:** DOC-001
**Priority:** Critical (P0)
**Estimated Effort:** 2-4 hours
**Target Version:** 1.8.1

## Problem Statement

The README.md file contains broken code examples that reference the old package name `forge` instead of the current package name `code_forge`. This was caused by a package rename at v1.1.0 that was not propagated to all documentation.

**Impact:**
- Every programmatic usage example in README causes ImportError
- New users cannot copy-paste examples to get started
- Hurts project credibility and adoption
- Creates confusion about the actual package structure

## Scope

### In Scope
1. Update all `forge.` imports to `code_forge.` in README.md
2. Update project structure diagram to show `src/code_forge/` instead of `src/forge/`
3. Verify all code examples are syntactically correct
4. Update any other documentation files referencing old package name

### Out of Scope
- Adding new documentation
- Restructuring documentation
- Updating API documentation (different phase)

## Implementation Plan

### Step 1: Audit README.md
1. Identify all occurrences of `forge.` imports
2. Identify all occurrences of `src/forge/` paths
3. Document each location requiring change

### Step 2: Update Package References
1. Replace `from forge.` with `from code_forge.`
2. Replace `import forge.` with `import code_forge.`
3. Replace `src/forge/` with `src/code_forge/`
4. Replace standalone `forge/` directory references

### Step 3: Verify Examples
1. Extract all code examples from README
2. Verify each example is syntactically valid Python
3. Spot-check critical examples actually work

### Step 4: Check Other Documentation
1. Scan `docs/` directory for old package references
2. Update any found occurrences

## Files to Modify

| File | Changes Required |
|------|------------------|
| `README.md` | ~50 occurrences of `forge.` to `code_forge.` |
| `docs/*.md` | Audit and update as needed |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed occurrences | Medium | Low | Grep verification after changes |
| Breaking working links | Low | Low | Only changing package names, not URLs |
| Introducing typos | Low | Medium | Review before commit |

## Success Metrics

1. Zero occurrences of `forge.` (not `code_forge.`) in README.md
2. All code examples can be parsed by Python without SyntaxError
3. Project structure diagram matches actual directory structure
