# Development Guardrails

Guidelines for maintaining code quality, honesty, and consistency throughout the Code-Forge project.

---

## 1. Status Reporting

### ❌ Don't

```
Status: Complete
- Fixed all the issues
- Everything works now
- Tests pass
```

### ✅ Do

```
Status: Planning Complete, Implementation Not Started
- Planning documents created in .ai/phase/1.1/
- No implementation code exists yet
- No tests exist yet
```

### ❌ Don't

Claim work is done without verification:
```
I've fixed the thread safety issues in the ToolRegistry.
```

### ✅ Do

State exactly what was done and what remains:
```
I've updated the PLAN.md to include thread safety patterns.
The actual ToolRegistry implementation does not exist yet.
```

---

## 2. Before Writing Code

### ❌ Don't

Start coding immediately when asked to implement something.

### ✅ Do

1. Check if planning documents exist for this phase
2. Read PLAN.md to understand the design
3. Read COMPLETION_CRITERIA.md to understand what "done" means
4. Read DEPENDENCIES.md to understand prerequisites
5. Verify dependencies are implemented
6. Only then begin implementation

### ❌ Don't

```python
# Let me just write this real quick
class ToolRegistry:
    def __init__(self):
        self.tools = {}
```

### ✅ Do

```
Before implementing ToolRegistry, let me verify:
1. Does .ai/phase/2.1/PLAN.md exist? Yes
2. What does it specify for ToolRegistry? [read and summarize]
3. Are dependencies (Phase 1.1) implemented? [check]
4. Now I'll implement according to the plan.
```

---

## 3. Verifying Claims

### ❌ Don't

Assume something exists because it should exist.

### ✅ Do

Use tools to verify before making claims:

```
# Before saying "the tests pass"
ls tests/
pytest tests/ -v

# Before saying "the module exists"
ls src/code_forge/core/

# Before saying "the function works"
python -c "from code_forge.core import Result; print(Result.ok('test'))"
```

### ❌ Don't

```
The OpenRouterClient is implemented and working.
```

### ✅ Do

```
Let me check if OpenRouterClient exists:
- File exists: [check forge/llm/client.py]
- Can import: [try importing]
- Tests pass: [run tests]

Result: The file does not exist. Only planning documents exist.
```

---

## 4. Error Handling

### ❌ Don't

```python
def get_config(path):
    with open(path) as f:
        return json.load(f)
```

### ✅ Do

```python
def get_config(path: Path) -> Result[Config, ConfigError]:
    """Load configuration from file.

    Args:
        path: Path to configuration file.

    Returns:
        Result containing Config on success, ConfigError on failure.
    """
    if not path.exists():
        return Result.err(ConfigError(f"File not found: {path}"))

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return Result.err(ConfigError(f"Invalid JSON: {e}"))
    except OSError as e:
        return Result.err(ConfigError(f"Cannot read file: {e}"))

    try:
        config = Config.from_dict(data)
    except ValidationError as e:
        return Result.err(ConfigError(f"Invalid config: {e}"))

    return Result.ok(config)
```

---

## 5. Thread Safety

### ❌ Don't

```python
class Registry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.items = {}
        return cls._instance

    def register(self, name, item):
        if name in self.items:
            raise ValueError("Already registered")
        self.items[name] = item  # Race condition
```

### ✅ Do

```python
class Registry:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.items = {}
                cls._instance._lock = threading.RLock()
        return cls._instance

    def register(self, name: str, item: Any) -> None:
        with self._lock:
            if name in self.items:
                raise ValueError("Already registered")
            self.items[name] = item
```

---

## 6. Resource Management

### ❌ Don't

```python
class Client:
    def __init__(self):
        self.connection = create_connection()

    def request(self, data):
        return self.connection.send(data)
```

### ✅ Do

```python
class Client:
    def __init__(self):
        self._connection = None
        self._closed = False

    async def connect(self) -> None:
        if self._closed:
            raise RuntimeError("Client is closed")
        self._connection = await create_connection()

    async def request(self, data: bytes) -> bytes:
        if self._connection is None:
            raise RuntimeError("Not connected")
        return await self._connection.send(data)

    async def close(self) -> None:
        if self._connection and not self._closed:
            await self._connection.close()
            self._connection = None
        self._closed = True

    async def __aenter__(self) -> "Client":
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def __del__(self) -> None:
        if self._connection and not self._closed:
            warnings.warn(
                "Client was not closed. Use 'async with' or call close().",
                ResourceWarning,
            )
```

---

## 7. Input Validation

### ❌ Don't

```python
def read_file(path, limit):
    with open(path, "rb") as f:
        return f.read(limit)
```

### ✅ Do

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def read_file(path: Path, limit: int | None = None) -> Result[bytes, FileError]:
    """Read file with size validation.

    Args:
        path: File to read.
        limit: Maximum bytes to read (default: MAX_FILE_SIZE).

    Returns:
        Result with file contents or error.
    """
    if not path.exists():
        return Result.err(FileError(f"File not found: {path}"))

    if not path.is_file():
        return Result.err(FileError(f"Not a file: {path}"))

    limit = limit or MAX_FILE_SIZE
    if limit <= 0:
        return Result.err(FileError("Limit must be positive"))

    try:
        size = path.stat().st_size
        if size > limit:
            return Result.err(FileError(
                f"File too large: {size} bytes (max: {limit})"
            ))

        with open(path, "rb") as f:
            return Result.ok(f.read())

    except OSError as e:
        return Result.err(FileError(f"Cannot read file: {e}"))
```

---

## 8. Mutable Defaults

### ❌ Don't

```python
def process(items=[]):
    items.append("processed")
    return items

class Config:
    def __init__(self, options={}):
        self.options = options
```

### ✅ Do

```python
def process(items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append("processed")
    return items

class Config:
    def __init__(self, options: dict[str, Any] | None = None):
        self.options = options if options is not None else {}

# Or with dataclasses:
@dataclass
class Config:
    options: dict[str, Any] = field(default_factory=dict)
```

---

## 9. Asyncio Patterns

### ❌ Don't

```python
class Manager:
    def __init__(self):
        self._lock = asyncio.Lock()  # Fails outside async context
        self._semaphore = asyncio.Semaphore(5)
```

### ✅ Do

```python
class Manager:
    def __init__(self):
        self._lock: asyncio.Lock | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._max_concurrent = 5

    def _get_lock(self) -> asyncio.Lock:
        """Lazy initialization for async context."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Lazy initialization for async context."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    async def do_work(self) -> None:
        async with self._get_lock():
            # protected work
            pass
```

---

## 10. Security

### ❌ Don't

```python
def run_command(user_input):
    os.system(f"echo {user_input}")

def render_template(template, user_data):
    return template.format(**user_data)
```

### ✅ Do

```python
def run_command(args: list[str]) -> subprocess.CompletedProcess:
    """Run command without shell injection risk."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=30,
    )

def render_template(template: str, user_data: dict[str, str]) -> str:
    """Render template with sanitized values."""
    sanitized = {
        key: _sanitize_value(value)
        for key, value in user_data.items()
    }
    return template.format(**sanitized)

def _sanitize_value(value: str) -> str:
    """Remove potentially dangerous characters."""
    # Remove null bytes, limit length
    value = value.replace('\x00', '')
    if len(value) > 8192:
        value = value[:8192]
    return value
```

---

## 11. Bounded Collections

### ❌ Don't

```python
class Cache:
    def __init__(self):
        self.items = {}

    def set(self, key, value):
        self.items[key] = value  # Unbounded growth
```

### ✅ Do

```python
class Cache:
    def __init__(self, max_size: int = 1000):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._items: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            # Remove if exists (to update LRU order)
            if key in self._items:
                del self._items[key]

            # Evict oldest if at capacity
            while len(self._items) >= self._max_size:
                self._items.popitem(last=False)

            self._items[key] = value

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._items:
                # Move to end (most recently used)
                self._items.move_to_end(key)
                return self._items[key]
            return None
```

---

## 12. Documentation

### ❌ Don't

```python
def proc(x, y, z=None):
    # do stuff
    if z:
        return x + y + z
    return x + y
```

### ✅ Do

```python
def calculate_sum(
    first: int,
    second: int,
    third: int | None = None,
) -> int:
    """Calculate the sum of two or three integers.

    Args:
        first: First integer to add.
        second: Second integer to add.
        third: Optional third integer to add.

    Returns:
        Sum of the provided integers.

    Examples:
        >>> calculate_sum(1, 2)
        3
        >>> calculate_sum(1, 2, 3)
        6
    """
    total = first + second
    if third is not None:
        total += third
    return total
```

---

## 13. Testing Claims

### ❌ Don't

Say "tests pass" without running them.

### ✅ Do

```bash
# Actually run the tests
pytest tests/unit/test_result.py -v

# Show the output
===== test session starts =====
collected 5 items

test_result.py::test_ok_value PASSED
test_result.py::test_err_value PASSED
test_result.py::test_unwrap_ok PASSED
test_result.py::test_unwrap_err_raises PASSED
test_result.py::test_map PASSED

===== 5 passed in 0.03s =====

# Now you can say "tests pass"
```

---

## 14. Debugging Before Fixing

### ❌ Don't

```
The function is broken. Let me change this line and see if it works.
[changes code randomly]
```

### ✅ Do

```
The function is broken. Let me investigate:

1. What is the expected behavior?
   - Input: [x, y, z]
   - Expected output: [result]

2. What is the actual behavior?
   - Actual output: [wrong result]
   - Error message: [if any]

3. Where does it go wrong?
   [add logging or debugger]
   - Line 10: value is correct
   - Line 15: value becomes incorrect

4. Why does it go wrong?
   - Line 12 modifies the value incorrectly because [reason]

5. What is the fix?
   - Change line 12 from [X] to [Y] because [reason]

6. Does the fix work?
   [test and verify]
```

---

## 15. Commit Messages

### ❌ Don't

```
fix stuff
updates
wip
asdf
```

### ✅ Do

```
Add thread-safe locking to ToolRegistry

The ToolRegistry singleton was susceptible to race conditions when
multiple threads called register() simultaneously. Added RLock to
protect all mutations.

Fixes #123
```

---

## Summary Checklist

Before claiming any work is complete:

- [ ] Does the implementation code actually exist?
- [ ] Can you import it without errors?
- [ ] Do tests exist?
- [ ] Do tests pass?
- [ ] Did you run the tests yourself?
- [ ] Does it meet all completion criteria?
- [ ] Have you verified each claim with evidence?
