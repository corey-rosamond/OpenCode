# FEAT-001: Per-Project RAG Support - Code Review Checklist

**Phase:** per-project-rag
**Version Target:** 1.9.0

---

## Pre-Review Verification

Before submitting for review, verify:

- [ ] All tests pass: `pytest tests/unit/rag tests/integration/rag -v`
- [ ] Type checking passes: `mypy src/code_forge/rag/`
- [ ] Linting passes: `ruff check src/code_forge/rag/`
- [ ] Coverage >90%: `pytest --cov=src/code_forge/rag --cov-fail-under=90`
- [ ] No TODO comments left in code
- [ ] All public APIs have docstrings

---

## Code Quality Checklist

### Architecture

- [ ] Follows existing Code-Forge patterns
- [ ] Protocol-based abstractions for extensibility
- [ ] Clear separation between modules
- [ ] No circular imports
- [ ] Dependencies are lazy-loaded

### Models (rag/models.py)

- [ ] All models inherit from `pydantic.BaseModel`
- [ ] All fields have type annotations
- [ ] Optional fields have `| None` type
- [ ] Default values use `Field(default_factory=...)` for mutable types
- [ ] Validators are `@field_validator` decorated
- [ ] Models have docstrings explaining purpose
- [ ] `model_config = ConfigDict(validate_assignment=True)` where appropriate

### Configuration (rag/config.py)

- [ ] `RAGConfig` follows `CodeForgeConfig` patterns
- [ ] All settings have sensible defaults
- [ ] Validation for numeric ranges
- [ ] Enum types for constrained choices
- [ ] Documentation for each setting

### Async Patterns

- [ ] All I/O operations are async
- [ ] CPU-bound work runs in executor
- [ ] No blocking calls in async functions
- [ ] Proper exception handling in async code
- [ ] Cleanup in finally blocks

### Error Handling

- [ ] All errors have informative messages
- [ ] No bare `except:` clauses
- [ ] User-facing errors are clear and actionable
- [ ] Internal errors are logged
- [ ] No sensitive information in error messages

### Logging

- [ ] Uses `logging.getLogger(__name__)`
- [ ] Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] No print statements
- [ ] Logs include relevant context

---

## Security Review

### File System Access

- [ ] Path traversal prevention (no `..` in paths)
- [ ] File permissions respected
- [ ] No execution of file contents
- [ ] Temporary files cleaned up
- [ ] Index directory permissions appropriate

### Data Handling

- [ ] No sensitive data in logs
- [ ] No credentials in index
- [ ] Safe deserialization (no pickle)
- [ ] Input validation for file paths

### Network (if OpenAI embeddings)

- [ ] API key not logged
- [ ] HTTPS only
- [ ] Timeout configuration
- [ ] Rate limiting awareness

---

## Performance Review

### Memory

- [ ] Large files streamed, not loaded entirely
- [ ] Embeddings generated in batches
- [ ] Vector store uses disk, not memory
- [ ] No memory leaks in long-running operations
- [ ] Lazy loading for optional dependencies

### Speed

- [ ] Incremental indexing avoids re-processing
- [ ] Batch operations where possible
- [ ] Index lookups are O(1) or O(log n)
- [ ] No N+1 query patterns
- [ ] File watching is efficient

### Scalability

- [ ] Tested with 1000+ files
- [ ] Tested with large files (500KB)
- [ ] Index size proportional to source size
- [ ] Search performance acceptable at scale

---

## Testing Review

### Unit Tests

- [ ] All public methods tested
- [ ] Edge cases covered
- [ ] Error conditions tested
- [ ] Mocks used appropriately
- [ ] No flaky tests

### Integration Tests

- [ ] End-to-end workflows tested
- [ ] Real components used (not just mocks)
- [ ] Cleanup after tests
- [ ] Tests are independent

### Fixtures

- [ ] Reusable fixtures created
- [ ] Sample project representative
- [ ] Mock providers available
- [ ] Temporary directories cleaned up

---

## Documentation Review

### Code Documentation

- [ ] All public classes have docstrings
- [ ] All public methods have docstrings
- [ ] Complex algorithms explained
- [ ] Type hints complete and accurate

### User Documentation

- [ ] README updated with RAG feature
- [ ] Configuration options documented
- [ ] Command usage documented
- [ ] Installation instructions clear

### Examples

- [ ] Configuration example provided
- [ ] Usage examples in docstrings
- [ ] CLI examples in help text

---

## Integration Review

### Configuration Integration

- [ ] `RAGConfig` added to `CodeForgeConfig`
- [ ] Environment variables mapped
- [ ] Config loading works at all levels
- [ ] Defaults are sensible

### Command Integration

- [ ] Commands registered in registry
- [ ] `CommandContext` has `rag_manager`
- [ ] Help text accurate
- [ ] Commands visible in `/help`

### Context Integration

- [ ] `RAGContextAugmenter` integrates smoothly
- [ ] Token counting accurate
- [ ] Doesn't break existing context flow
- [ ] Augmentation is optional

---

## Backwards Compatibility

- [ ] No breaking changes to existing APIs
- [ ] Existing tests still pass
- [ ] Config files without `rag` section work
- [ ] RAG disabled by default doesn't affect existing behavior
- [ ] Optional dependencies don't break import

---

## Final Checks

### Before Merge

- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] UNDONE.md updated (FEAT-001 marked complete)
- [ ] All review comments addressed
- [ ] CI/CD pipeline passes
- [ ] Performance benchmarks pass

### Post-Merge

- [ ] Verify pip install works: `pip install code-forge[rag]`
- [ ] Verify `/rag index` works on real project
- [ ] Verify `/rag search` returns results
- [ ] Monitor for issues in first week

---

## Reviewer Sign-Off

| Aspect | Reviewer | Date | Status |
|--------|----------|------|--------|
| Architecture | | | |
| Code Quality | | | |
| Security | | | |
| Performance | | | |
| Testing | | | |
| Documentation | | | |
| Integration | | | |
| **Final Approval** | | | |
