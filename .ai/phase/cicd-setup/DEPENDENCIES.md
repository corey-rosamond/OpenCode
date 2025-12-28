# Dependencies: CI/CD Pipeline Setup

## Phase Dependencies

### Depends On (Blockers)
None. Can be implemented independently.

### Recommended Before
- DOC-001 (README fix) - Ensures examples in tests pass
- CODE-001 (ToolCategory fix) - Ensures all tests pass

### Blocks (Downstream)
- All future development benefits from CI/CD
- Branch protection setup (needs working checks)

## Technical Dependencies

### Required Services
- GitHub repository with Actions enabled
- (Optional) Codecov account for coverage

### Required Secrets
None required for basic setup. Optional:
- `CODECOV_TOKEN` - For private repo coverage uploads

### GitHub Actions
Actions to be used:
- `actions/checkout@v4` - Repository checkout
- `actions/setup-python@v5` - Python environment
- `codecov/codecov-action@v4` - Coverage upload
- `softprops/action-gh-release@v1` - Release creation

## Knowledge Dependencies

### Required Understanding
- GitHub Actions workflow syntax
- YAML configuration
- pytest invocation
- mypy/ruff configuration

### Recommended Reading
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [actions/setup-python](https://github.com/actions/setup-python)
- Existing `pyproject.toml` dev dependencies
- `pytest.ini` or pytest configuration

## Integration Points

### Repository Configuration
| Setting | Requirement |
|---------|-------------|
| Actions | Must be enabled |
| Branch protection | Recommended after setup |
| Secrets | Optional for codecov |

### Files to Coordinate With
| File | Reason |
|------|--------|
| `pyproject.toml` | Dev dependencies for CI |
| `tests/README.md` | Update CI/CD section |
| `.gitignore` | Ensure workflows not ignored |

### External Services
| Service | Purpose | Required? |
|---------|---------|-----------|
| GitHub Actions | CI execution | Yes |
| Codecov | Coverage tracking | No |

## Rollback Plan

If workflows cause issues:
1. Delete `.github/workflows/*.yml` files
2. Or disable workflow via GitHub UI
3. Branch protection can be disabled in settings

Low risk - workflows don't affect repository code.

## Testing Strategy

### Local Validation
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"

# Simulate job locally (requires act)
act -j test -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
```

### GitHub Validation
1. Push workflow files to a test branch
2. Create draft PR to trigger workflow
3. Verify workflow runs successfully
4. Merge when confirmed working
