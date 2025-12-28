# Test Strategy: Documentation Fix

## Test Approach

Since this phase is documentation-only, traditional unit tests don't apply. Instead, we use verification scripts and manual checks.

## Automated Verification

### V-1: No Old Package References
```bash
# Should return exit code 1 (no matches)
grep -E "from forge\." README.md && exit 1 || exit 0
grep -E "import forge\." README.md && exit 1 || exit 0
grep -E "src/forge/" README.md && exit 1 || exit 0
```

### V-2: Package References Present
```bash
# Should return exit code 0 (matches found)
grep -E "from code_forge\." README.md || exit 1
grep -E "src/code_forge/" README.md || exit 1
```

### V-3: Python Syntax Validation
```python
#!/usr/bin/env python3
"""Validate Python code blocks in README.md"""
import ast
import re
import sys

def extract_python_blocks(markdown_file):
    """Extract Python code blocks from markdown."""
    with open(markdown_file) as f:
        content = f.read()

    # Match ```python ... ``` blocks
    pattern = r'```python\n(.*?)```'
    blocks = re.findall(pattern, content, re.DOTALL)
    return blocks

def validate_syntax(code):
    """Check if code is valid Python syntax."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    blocks = extract_python_blocks('README.md')
    errors = []

    for i, block in enumerate(blocks, 1):
        valid, error = validate_syntax(block)
        if not valid:
            errors.append(f"Block {i}: {error}")

    if errors:
        print("Syntax errors found:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print(f"All {len(blocks)} Python blocks are syntactically valid")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

### V-4: Import Verification
```python
#!/usr/bin/env python3
"""Verify key imports from README examples work."""
import sys

def test_imports():
    errors = []

    # Test tool imports
    try:
        from code_forge.tools.file import ReadTool, WriteTool
    except ImportError as e:
        errors.append(f"Tool imports: {e}")

    # Test permission imports
    try:
        from code_forge.permissions import PermissionChecker, PermissionLevel
    except ImportError as e:
        errors.append(f"Permission imports: {e}")

    # Test session imports
    try:
        from code_forge.sessions import SessionManager
    except ImportError as e:
        errors.append(f"Session imports: {e}")

    # Test hook imports
    try:
        from code_forge.hooks import HookRegistry, HookExecutor
    except ImportError as e:
        errors.append(f"Hook imports: {e}")

    if errors:
        print("Import errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("All imports verified successfully")
    sys.exit(0)

if __name__ == '__main__':
    test_imports()
```

## Manual Verification

### M-1: Visual Inspection
1. Open README.md in GitHub preview
2. Verify code blocks render correctly
3. Verify project structure diagram is readable

### M-2: Copy-Paste Test
1. Copy "Quick Start" code example
2. Paste into Python REPL
3. Verify no import errors

### M-3: Link Verification
1. Click all links in README
2. Verify they resolve correctly

## Test Execution Order

1. Run V-1 (no old references)
2. Run V-2 (new references present)
3. Run V-3 (syntax validation)
4. Run V-4 (import verification)
5. Perform M-1 (visual inspection)
6. Perform M-2 (copy-paste test)

## Success Criteria

- All V-* verifications pass (exit code 0)
- All M-* manual checks pass
- No regressions in existing functionality
