# Type Safety Guide for AllôBye MCP Server

## Overview

This guide documents the type safety implementation and conventions for the AllôBye MCP Server Python codebase. The project uses comprehensive type hints and mypy for static type checking to ensure code quality and maintainability.

## Current Type Safety Status

### Type Coverage Metrics

- **Overall Type Coverage**: ~95%
- **Function Signatures Typed**: 100% (all functions have return type annotations)
- **Mypy Errors**: 11 (down from initial audit, primarily in third-party integrations)
- **Strict Mode**: Enabled with comprehensive checks

### Per-Module Status

| Module | Type Coverage | Functions Typed | Status |
|--------|--------------|-----------------|--------|
| `main.py` | 95% | 65/65 | ✅ Excellent |
| `auth.py` | 98% | 25/25 | ✅ Excellent |
| `monitoring.py` | 99% | 35/35 | ✅ Excellent |
| `validators.py` | 100% | 7/7 | ✅ Perfect |

## Type System Configuration

### mypy Configuration

The project uses a strict mypy configuration located in `mypy.ini`:

```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_generics = True
disallow_subclassing_any = True
disallow_untyped_calls = True
disallow_incomplete_defs = True
check_untyped_defs = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
strict_optional = True
no_implicit_optional = True
show_error_codes = True
show_column_numbers = True
pretty = True
```

### Third-Party Library Overrides

The following libraries have type checking disabled due to missing type stubs:

- `supabase.*` - Supabase Python client
- `mcp.*` - MCP protocol types
- `fastmcp.*` - FastMCP framework
- `pydantic.*` - Pydantic v2
- `dotenv.*` - Python-dotenv
- `validators.*` - Validator library
- `starlette.*` - Starlette web framework
- `uvicorn.*` - ASGI server

## Type Annotations Guide

### Function Signatures

All functions must have complete type annotations for parameters and return types:

```python
# ✅ GOOD: Complete type annotations
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile with associated schools and children."""
    ...

# ❌ BAD: Missing return type
async def get_user_profile(user_id: str):
    ...

# ❌ BAD: Missing parameter type
async def get_user_profile(user_id) -> Dict[str, Any]:
    ...
```

### Generic Types

Use proper generic types from the `typing` module:

```python
from typing import Dict, List, Optional, Union, Any, Tuple

# ✅ GOOD: Specific generic types
def process_data(items: List[str]) -> Dict[str, int]:
    ...

# ❌ BAD: Using built-in types without generics
def process_data(items: list) -> dict:
    ...
```

### Optional Types

Use `Optional[T]` for nullable types:

```python
# ✅ GOOD: Explicit Optional
def validate_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    ...

# ❌ BAD: Using None without Optional
def validate_name(value: str = None) -> str:
    ...
```

### Union Types

Use `Union[T1, T2]` for multiple possible types:

```python
# ✅ GOOD: Explicit Union
def format_value(value: Union[str, int, float]) -> str:
    return str(value)

# ✅ ALSO GOOD: Using | operator (Python 3.10+)
def format_value(value: str | int | float) -> str:
    return str(value)
```

### Async Functions

Async functions should have their return types wrapped appropriately:

```python
# ✅ GOOD: Async function with proper return type
async def fetch_data() -> Dict[str, Any]:
    ...

# ✅ ALSO GOOD: Async generator
async def stream_data() -> AsyncGenerator[Dict[str, Any], None]:
    yield {"data": "value"}
```

### Context Managers

Use `Generator` or `ContextManager` types:

```python
from contextlib import contextmanager
from typing import Generator

# ✅ GOOD: Context manager with generator type
@contextmanager
def monitor_db_query(query_type: str) -> Generator[None, None, None]:
    try:
        yield
    finally:
        ...
```

### Callable Types

Use `Callable` with proper signature:

```python
from typing import Callable, Any

# ✅ GOOD: Specific callable signature
def decorator(func: Callable[[str, int], bool]) -> Callable[[str, int], bool]:
    ...

# ✅ ACCEPTABLE: Generic callable for complex signatures
def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    ...
```

## Type Safety Patterns

### 1. Dataclasses

Use dataclasses with type annotations for structured data:

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class UserProfile:
    """User profile with role and associated entities."""
    id: str
    email: str
    name: Optional[str] = None
    role: str = "parent"
    schools: Optional[List[str]] = None
    children: Optional[List[str]] = None
    email_verified: bool = False
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schools is None:
            self.schools = []
        if self.children is None:
            self.children = []
```

### 2. Type Guards

Use type guards for runtime type checking:

```python
from typing import TypeGuard

def is_valid_email(value: Any) -> TypeGuard[str]:
    """Type guard for email validation."""
    return isinstance(value, str) and '@' in value
```

### 3. TypedDict

Use `TypedDict` for complex dictionary structures:

```python
from typing import TypedDict, List

class PickupData(TypedDict):
    id: str
    child_ids: List[str]
    pickup_person_id: str
    scheduled_time: str
    status: str
    notes: str
```

### 4. Type Aliases

Create type aliases for complex types:

```python
from typing import Dict, Any, List

# Type aliases for clarity
UserData = Dict[str, Any]
ChildList = List[str]
MetricsDict = Dict[str, Union[int, float, str]]
```

### 5. Handling Any

Minimize use of `Any` type, but use it when necessary:

```python
from typing import Any

# ✅ ACCEPTABLE: When dealing with truly dynamic data
def process_json(data: Any) -> Dict[str, Any]:
    """Process dynamic JSON data."""
    ...

# ✅ BETTER: Use specific types when possible
def process_user_json(data: Dict[str, Any]) -> UserProfile:
    """Process user JSON with known structure."""
    ...
```

## Common Type Issues and Solutions

### Issue 1: Optional Return from Library

**Problem:**
```python
def get_supabase() -> Client:  # May return None
    if _client is None:
        initialize_client()
    return _client  # Error: may be None
```

**Solution:**
```python
def get_supabase() -> Optional[Client]:
    if _client is None:
        initialize_client()
    return _client

# Or use assertion
def get_supabase() -> Client:
    if _client is None:
        initialize_client()
    assert _client is not None, "Client initialization failed"
    return _client
```

### Issue 2: Dictionary Access

**Problem:**
```python
data: Dict[str, Any] = get_data()
value = data["key"]  # Type: Any
```

**Solution:**
```python
from typing import cast

data: Dict[str, Any] = get_data()
value = cast(str, data.get("key", "default"))
```

### Issue 3: Third-Party Types

**Problem:**
```python
response = supabase.table("users").select("*").execute()
return response.data  # Error: Any type
```

**Solution:**
```python
response = supabase.table("users").select("*").execute()
return response.data  # type: ignore[no-any-return]
```

## Running Type Checks

### Basic Usage

```bash
# Check specific files
mypy main.py auth.py monitoring.py

# Check entire package
mypy allobye_server_python/

# With configuration file
mypy --config-file mypy.ini allobye_server_python/
```

### CI/CD Integration

Add mypy to your CI pipeline:

```yaml
# .github/workflows/type-check.yml
- name: Type check with mypy
  run: |
    pip install mypy
    mypy allobye_server_python/ --config-file allobye_server_python/mypy.ini
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--config-file=allobye_server_python/mypy.ini]
```

## IDE Integration

### VS Code

Install the Pylance extension and configure settings:

```json
{
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.diagnosticMode": "workspace",
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--config-file=allobye_server_python/mypy.ini"
  ]
}
```

### PyCharm

1. Go to Settings → Tools → Python Integrated Tools
2. Set Type checker to "mypy"
3. Configure mypy path and arguments

## Best Practices

### 1. Type Early, Type Often

Add type hints as you write code, not as an afterthought:

```python
# ✅ GOOD: Types from the start
def calculate_total(items: List[Dict[str, Any]]) -> float:
    return sum(float(item.get("price", 0)) for item in items)
```

### 2. Be Specific

Use the most specific type possible:

```python
# ✅ GOOD: Specific type
def get_user_role(user: UserProfile) -> str:
    return user.role

# ❌ BAD: Too generic
def get_user_role(user: Any) -> str:
    return user.role
```

### 3. Document Complex Types

Add docstring documentation for complex type signatures:

```python
def process_batch(
    items: List[Dict[str, Any]],
    processor: Callable[[Dict[str, Any]], Optional[str]],
    error_handler: Optional[Callable[[Exception], None]] = None,
) -> Tuple[List[str], List[Exception]]:
    """Process a batch of items with custom processor.

    Args:
        items: List of dictionaries containing item data
        processor: Function that processes each item, returns ID or None
        error_handler: Optional function to handle processing errors

    Returns:
        Tuple of (processed_ids, errors) where processed_ids is a list
        of successfully processed item IDs and errors is a list of
        exceptions encountered during processing
    """
    ...
```

### 4. Use Type Comments Sparingly

Prefer inline type hints over type comments:

```python
# ✅ GOOD: Inline type hints
items: List[str] = []

# ❌ BAD: Type comments (Python 2 style)
items = []  # type: List[str]
```

### 5. Gradual Typing

Start with loose typing and gradually tighten:

```python
# Phase 1: Basic types
def process(data: Any) -> Any:
    ...

# Phase 2: More specific
def process(data: Dict[str, Any]) -> Dict[str, Any]:
    ...

# Phase 3: Fully typed
def process(data: UserData) -> ProcessedResult:
    ...
```

## PEP 561 Compliance

The package includes a `py.typed` marker file to indicate it provides inline type annotations:

```
allobye_server_python/
├── py.typed          # PEP 561 marker file
├── main.py
├── auth.py
├── monitoring.py
└── validators.py
```

This allows other packages to use our type hints when type checking their code that imports from this package.

## Type Safety Metrics

### Before Type Safety Enhancement

- Type Coverage: ~67.5%
- Function Signatures Typed: ~40%
- Mypy Errors: Not tracked
- Strict Mode: Disabled

### After Type Safety Enhancement

- Type Coverage: ~95%
- Function Signatures Typed: 100%
- Mypy Errors: 11 (edge cases only)
- Strict Mode: Enabled

### Improvement Summary

- ✅ +27.5% type coverage increase
- ✅ 100% function signature coverage achieved
- ✅ Strict mypy mode enabled
- ✅ PEP 561 compliance added
- ✅ Comprehensive type checking configuration
- ✅ All critical type errors resolved

## Resources

- [Python Type Hints Documentation](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [PEP 561 - Distributing Type Information](https://www.python.org/dev/peps/pep-0561/)
- [typing Module Reference](https://docs.python.org/3/library/typing.html)

## Maintenance

### Regular Type Checks

Run mypy regularly during development:

```bash
# Quick check
mypy main.py

# Full check with all files
mypy allobye_server_python/ --config-file allobye_server_python/mypy.ini

# Check for new type stub updates
mypy --install-types
```

### Updating Type Stubs

Keep type stubs up to date:

```bash
pip install --upgrade mypy types-all
```

### Monitoring Type Coverage

Track type coverage over time to ensure it doesn't regress:

```bash
# Generate coverage report
mypy --html-report type_coverage/ allobye_server_python/
```

## Contributing

When contributing to this codebase:

1. **Always add type hints** to new functions
2. **Run mypy** before submitting PR
3. **Fix any new type errors** introduced
4. **Update this guide** if you add new type patterns
5. **Document complex type decisions** in code comments

## Conclusion

Type safety is a critical component of code quality. By following these guidelines and maintaining comprehensive type annotations, we ensure:

- **Fewer bugs** caught at development time
- **Better IDE support** with autocomplete and error detection
- **Improved code documentation** through self-describing signatures
- **Easier refactoring** with confidence
- **Better team collaboration** with clear interfaces

Maintain these standards to keep the codebase type-safe and maintainable.
