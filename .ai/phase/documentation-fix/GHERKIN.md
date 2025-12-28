# Gherkin Specifications: Documentation Fix

## Feature: README Package References

### Scenario: Import statements use correct package name
```gherkin
Given the README.md file exists
When I search for Python import statements
Then all imports should reference "code_forge" package
And no imports should reference "forge" package alone
```

### Scenario: Project structure diagram is accurate
```gherkin
Given the README.md contains a project structure diagram
When I compare it to the actual directory structure
Then the diagram should show "src/code_forge/"
And the diagram should not show "src/forge/"
```

### Scenario: Code examples are syntactically valid
```gherkin
Given a Python code example from README.md
When I parse it with Python's ast module
Then it should parse without SyntaxError
```

### Scenario: Tool import example works
```gherkin
Given the README example:
  """
  from code_forge.tools.file import ReadTool, WriteTool
  """
When I execute this import in Python
Then the import should succeed without ImportError
And ReadTool and WriteTool should be valid classes
```

### Scenario: Permission system example works
```gherkin
Given the README example:
  """
  from code_forge.permissions import PermissionChecker, PermissionLevel
  """
When I execute this import in Python
Then the import should succeed without ImportError
And PermissionChecker should be a valid class
And PermissionLevel should be a valid enum
```

### Scenario: Session management example works
```gherkin
Given the README example:
  """
  from code_forge.sessions import SessionManager, Session
  """
When I execute this import in Python
Then the import should succeed without ImportError
And SessionManager should be a valid class
```

## Feature: Documentation Consistency

### Scenario: No old package references remain
```gherkin
Given the documentation files in the repository
When I search for "forge." not preceded by "code_"
Then zero matches should be found in README.md
And zero matches should be found in docs/*.md
```

### Scenario: grep verification passes
```gherkin
Given the completed documentation updates
When I run: grep -r "from forge\." README.md
Then the exit code should be 1 (no matches)
When I run: grep -r "src/forge/" README.md
Then the exit code should be 1 (no matches)
```
