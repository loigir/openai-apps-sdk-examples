# AllôBye Testing Guide

## Overview

Comprehensive testing suite for the AllôBye MCP Server with **80+ test cases** covering:
- All 10 MCP tools
- Complete authentication flows
- Authorization and security
- End-to-end integration scenarios
- Edge cases and error handling

**Target Coverage:** 80% overall, with 90%+ for critical paths.

---

## Test Suite Structure

### 1. **test_mcp_tools.py** (40+ tests)
Tests all 10 MCP tools with happy paths and error cases:

#### Authentication Tools (5 tools, ~20 tests)
- `auth-signup`: Valid/invalid passwords, rate limiting, role-based signup
- `auth-login`: Successful login, wrong credentials, rate limiting, account lockout
- `auth-logout`: Valid/invalid tokens
- `auth-reset-password`: Email validation
- `auth-profile`: Session validation, profile retrieval

#### Pickup Management Tools (3 tools, ~15 tests)
- `pickup-schedule-create`: Single/multi-child pickups, cross-school coordination, XSS protection
- `delegate-authorize`: Valid/invalid emails, permissions validation, multi-school sync
- `emergency-declare`: Different emergency types, XSS sanitization, delegate notification

#### Dashboard Tools (2 tools, ~5 tests)
- `school-dashboard-fetch`: Role-based access, time windows, staff authorization
- `monitoring-dashboard-fetch`: With/without details, default parameters

### 2. **test_auth_complete.py** (35+ tests)
Comprehensive authentication and security tests:

#### Signup Tests (~8 tests)
- Parent and staff signup
- Password strength validation (all rules)
- Rate limiting enforcement

#### Login Tests (~7 tests)
- Successful login
- Invalid credentials
- Rate limiting
- Account lockout after failed attempts
- Lockout clearing

#### Session Management (~6 tests)
- Session validation
- Token refresh
- Logout
- Session expiration
- Refresh token rotation

#### Profile Management (~4 tests)
- Get user profile
- Update name
- Update schools (for staff)

#### Authorization (~5 tests)
- Parent-child ownership verification
- Staff-school verification
- Child linking

#### Password Validation (~9 tests)
- Length, uppercase, lowercase, digit, special char requirements
- Common password rejection
- Sequential character detection

#### Rate Limiting (~3 tests)
- Per-email enforcement
- Maximum attempts
- Independent limits per email

#### Account Lockout (~3 tests)
- Lockout after max failures
- Lockout clearing
- Login prevention when locked

### 3. **test_integration.py** (15+ tests)
End-to-end integration scenarios:

#### Complete User Journeys (~3 tests)
- Parent: signup → login → schedule pickup
- Staff: signup → login → access dashboard
- Session flow: signup → login → validate

#### Cross-School Coordination (~2 tests)
- Multi-school pickup scheduling
- Multi-school delegate authorization

#### Emergency Cascade (~2 tests)
- Delegate and school notifications
- Different emergency types

#### Authorization Workflows (~4 tests)
- Parent cannot access others' children
- Parent cannot access staff dashboard
- Staff cannot authorize delegates
- Staff can only access their schools

#### Complex Scenarios (~4 tests)
- Complete day workflow (signup → delegate → pickup → emergency)
- Concurrent pickups by different parents
- XSS protection across entire workflow

### 4. **conftest.py**
Shared fixtures and test utilities:
- Mock Supabase client with full auth simulation
- Authenticated user/staff fixtures
- Mock data for children, schools, delegates
- Rate limit clearing
- Time freezing utilities

---

## Running Tests

### Install Dependencies

```bash
cd allobye_server_python
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-timeout
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_mcp_tools.py
pytest test_auth_complete.py
pytest test_integration.py
```

### Run Tests by Category

```bash
# Run only authentication tests
pytest -m auth

# Run only MCP tool tests
pytest -m mcp_tools

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run only security tests
pytest -m security
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Run Specific Tests

```bash
# Run specific test class
pytest test_mcp_tools.py::TestAuthSignup

# Run specific test
pytest test_mcp_tools.py::TestAuthSignup::test_signup_success

# Run tests matching pattern
pytest -k "signup"
pytest -k "password"
```

---

## Test Coverage Goals

| Component | Target Coverage | Critical? |
|-----------|----------------|-----------|
| **MCP Tools** | 90% | ✓ Yes |
| **Authentication** | 95% | ✓ Yes |
| **Authorization** | 90% | ✓ Yes |
| **Input Validation** | 100% | ✓ Yes |
| **Error Handling** | 85% | Yes |
| **Database Helpers** | 70% | No |
| **Monitoring** | 60% | No |
| **Overall** | **80%** | ✓ Yes |

---

## Test Categories

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests across modules
- `@pytest.mark.auth` - Authentication and authorization tests
- `@pytest.mark.mcp_tools` - MCP tool handler tests
- `@pytest.mark.security` - Security feature tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.mock` - Tests using mocked dependencies
- `@pytest.mark.requires_db` - Tests requiring database connection

---

## Writing New Tests

### Test Structure Template

```python
import pytest

@pytest.mark.asyncio  # For async tests
@pytest.mark.auth  # Add relevant markers
class TestMyFeature:
    """Test my feature functionality."""

    async def test_happy_path(self, authenticated_user):
        """Test successful case."""
        # Arrange
        input_data = {...}

        # Act
        result = await my_function(input_data)

        # Assert
        assert result is not None
        assert result["status"] == "success"

    async def test_error_case(self, authenticated_user):
        """Test error handling."""
        # Arrange
        invalid_data = {...}

        # Act & Assert
        with pytest.raises(MyException):
            await my_function(invalid_data)
```

### Using Fixtures

```python
async def test_with_fixtures(
    authenticated_user,  # Authenticated parent user
    authenticated_staff,  # Authenticated staff user
    mock_supabase_patch,  # Mocked Supabase client
    mock_children_data,  # Mock children in database
    mock_schools_data,  # Mock schools in database
    clear_rate_limits,  # Clear rate limiting
):
    """Test using multiple fixtures."""
    # Test implementation
```

### Testing Error Cases

```python
# Test validation errors
async def test_invalid_input(self):
    with pytest.raises(ValidationError):
        await function_with_validation(invalid_input)

# Test authentication errors
async def test_unauthorized(self):
    result = await protected_function(no_auth_token)
    assert result.isError
    assert "authentification" in result.content[0].text.lower()
```

---

## Continuous Integration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        cd allobye_server_python
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run tests with coverage
      run: |
        cd allobye_server_python
        pytest --cov=. --cov-report=xml --cov-report=term

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./allobye_server_python/coverage.xml
```

---

## Debugging Tests

### Run with Debug Output

```bash
# Show print statements
pytest -s

# Show full error traces
pytest --tb=long

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf
```

### Debug in VS Code

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v",
        "-s",
        "${file}"
      ],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/allobye_server_python"
    }
  ]
}
```

---

## Common Issues

### 1. **Async Tests Not Running**

Make sure pytest-asyncio is installed and `asyncio_mode = auto` is in `pytest.ini`.

### 2. **Rate Limiting Failures**

Use the `clear_rate_limits` fixture to reset rate limiting between tests:

```python
async def test_my_function(clear_rate_limits):
    # Rate limits are now clear
```

### 3. **Mock Data Not Found**

Ensure you're using fixtures to populate mock data:

```python
async def test_with_data(mock_supabase_patch, mock_children_data):
    # Children data is now in mock database
```

### 4. **Authentication Failures**

Use `authenticated_user` or `authenticated_staff` fixtures:

```python
async def test_protected_endpoint(authenticated_user):
    result = await endpoint(authenticated_user["access_token"])
```

---

## Performance Testing

### Measure Test Performance

```bash
# Show slowest 10 tests
pytest --durations=10

# Profile test execution
pytest --profile

# Run with timeout (30s default)
pytest --timeout=30
```

---

## Test Statistics

**Current Test Count:** 80+ tests

### Breakdown by Category:
- **MCP Tools:** 40+ tests
- **Authentication:** 35+ tests
- **Integration:** 15+ tests
- **Security:** Covered across all categories

### Breakdown by Type:
- **Happy Path:** ~40 tests
- **Error Cases:** ~30 tests
- **Edge Cases:** ~10 tests

### Expected Results:
- **Pass Rate:** 100%
- **Coverage:** 80%+ overall
- **Execution Time:** < 30 seconds

---

## Next Steps

1. **Run the full test suite:**
   ```bash
   pytest -v --cov=. --cov-report=html
   ```

2. **Review coverage report:**
   ```bash
   open htmlcov/index.html
   ```

3. **Add missing tests** for any uncovered critical paths

4. **Set up CI/CD** to run tests automatically

5. **Monitor test health** and update as code evolves

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

## Contact

For questions about the test suite, please refer to:
- **Main documentation:** README.md
- **Security documentation:** SECURITY.md
- **API documentation:** API.md
