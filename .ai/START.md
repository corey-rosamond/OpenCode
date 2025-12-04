# OpenCode AI Entry Point

**STOP. Read this entire file before doing anything else.**

---

## Project Context

**OpenCode** is a Claude Code alternative that provides:
- Access to 400+ AI models via OpenRouter API
- LangChain 1.0 integration for agent orchestration
- Full CLI experience with tools, permissions, sessions, and extensibility

The project has 22 phases with complete planning documentation. Phases 1.1-1.3, 2.1-2.3, 3.1-3.2, 4.1-4.2, 5.1-5.2, 6.1, and 6.2 are complete.

---

## Current Phase

```
CURRENT_PHASE: 7.1
```

**Phase Name:** Subagents System

**Phase Directory:** `.ai/phase/7.1/`

---

## Startup Sequence

Execute these steps in order every time you begin work on this project:

### Step 1: Read Governance Documents

1. Read `.ai/PERSONA.md` - Understand your working style and principles
2. Read `.ai/GUARDRAILS.md` - Understand what to do and what not to do

### Step 2: Read Current Phase Documentation

Read all files in the current phase directory (`.ai/phase/7.1/`):

1. `PLAN.md` - Architectural design and implementation details
2. `COMPLETION_CRITERIA.md` - What "done" means for this phase
3. `REQUIREMENTS.md` - Functional/non-functional requirements and dependencies
4. `GHERKIN.md` - Behavior specifications in Given/When/Then format
5. `UML.md` - Class diagrams, sequence diagrams, and architecture visuals
6. `WIREFRAMES.md` - UI/UX specifications (where applicable)

### Step 3: Check Project Status

1. Read `.ai/UNDONE.md` - Current project roadmap and phase status
2. Verify dependencies are actually implemented (not just planned)
3. Check what was last worked on if resuming a session

### Step 4: Verify Before Starting

Before writing any code:

- [ ] Planning documents exist and have been read
- [ ] Dependencies are implemented and tested (not just planned)
- [ ] Completion criteria are understood
- [ ] You can explain what you're about to build and why

---

## Directories

| Directory | Purpose | Access |
|-----------|---------|--------|
| `.ai/phase/[X.X]/` | Phase planning documentation | Read before implementing that phase |
| `.ai/phase/reference/` | Reference materials only | **IGNORE unless explicitly told to read** |
| `src/opencode/` | Implementation source code | Create/modify during implementation |
| `tests/` | Test code | Create/modify during implementation |

---

## Verification Requirements

**Never assume. Always verify.**

Before claiming something exists:
```bash
ls path/to/directory
```

Before claiming code works:
```bash
python -c "from module import thing; print(thing)"
```

Before claiming tests pass:
```bash
pytest tests/ -v
```

Before claiming a phase is complete:
- [ ] All code implemented per PLAN.md
- [ ] All tests written per COMPLETION_CRITERIA.md test requirements
- [ ] All tests pass
- [ ] All completion criteria met per COMPLETION_CRITERIA.md
- [ ] All quality gates passed (mypy, ruff, coverage)

---

## What "Complete" Means

A phase is **NOT** complete when:
- Planning documents are written
- Code examples exist in PLAN.md
- You think it should work

A phase **IS** complete when:
- Implementation code exists in `src/opencode/`
- Tests exist in `tests/`
- All tests pass
- All COMPLETION_CRITERIA.md items are verified
- All quality gates passed (mypy strict, ruff, coverage ≥90%)

---

## Dependency Rules

**Before starting any phase:**

1. Check REQUIREMENTS.md for that phase (dependencies listed there)
2. Verify each dependency is actually implemented:
   - Source files exist in `src/opencode/`
   - Tests exist in `tests/`
   - Tests pass
   - UNDONE.md shows Implementation as "Done"

**Do not start a phase if its dependencies are not complete.**

---

## Session Continuity

When resuming work:

1. Read this file (START.md)
2. Check `.ai/UNDONE.md` for current status
3. Verify the last claimed state is accurate:
   - Do the files that should exist actually exist?
   - Do the tests that should pass actually pass?
4. Continue from verified state, not assumed state

---

## Red Flags - Stop Immediately If:

- No planning documents exist for the current phase
- Requirements are unclear or ambiguous
- You're tempted to skip testing
- You're about to claim something is "done" without verification
- You're copying code without understanding it
- You're fixing symptoms instead of root causes
- Dependencies are not actually implemented
- You're being asked to read from `.ai/phase/reference/` without explicit instruction

**When in doubt, stop and ask.**

---

## Updating Project State

### When a Task is Completed

Update `.ai/UNDONE.md`:
- Mark the specific task as complete
- Only mark as complete after verification

### When a Phase is Completed

**CRITICAL: Do this IMMEDIATELY after all tests pass and quality gates are verified. Do NOT wait to be asked. This is a mandatory part of phase completion.**

Perform these updates in order:

1. **Update `.ai/UNDONE.md`:**
   - Mark Implementation as "Done" in the phase table
   - Mark Testing as "Done" in the phase table
   - Add implementation details to "What Exists" section
   - Update test count
   - Update "Next Steps" to point to the next phase
   - Add entry to "Version History" table

2. **Update this file (`.ai/START.md`):**
   - Change `CURRENT_PHASE` to the next phase number
   - Update "Phase Name" to the next phase name
   - Update "Phase Directory" to `.ai/phase/[next]/`
   - Update the completed phases list in "Project Context"
   - Update the phase directory reference in "Step 2"

3. **Update project `README.md`:**
   - Update feature descriptions if applicable
   - Update project structure if new packages added
   - Update test count
   - Add documentation section for new functionality
   - Update roadmap table to show phase as Complete

**A phase is NOT complete until all three files are updated.**

### Phase Progression

```
1.1 -> 1.2 -> 1.3 -> 2.1 -> 2.2 -> 2.3 -> 3.1 -> 3.2 ->
4.1 -> 4.2 -> 5.1 -> 5.2 -> 6.1 -> 6.2 -> 7.1 -> 7.2 ->
8.1 -> 8.2 -> 9.1 -> 9.2 -> 10.1 -> 10.2
```

Note: Some phases can be parallelized. See `.ai/UNDONE.md` for the dependency tree.

---

## Quick Reference

| Document | Location | Purpose |
|----------|----------|---------|
| This file | `.ai/START.md` | Entry point, current phase |
| Persona | `.ai/PERSONA.md` | Working style and principles |
| Guardrails | `.ai/GUARDRAILS.md` | Do's and don'ts with examples |
| Roadmap | `.ai/UNDONE.md` | Project status and tracking |
| Phase Docs | `.ai/phase/[X.X]/` | Planning for each phase |

---

## Remember

> "Weeks of coding can save hours of planning."

> "Hope is not a strategy. Test."

> "A phase is not complete until you can prove it is complete."
