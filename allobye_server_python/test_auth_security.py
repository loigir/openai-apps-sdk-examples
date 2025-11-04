"""
Test suite for authentication security features.

Tests password validation, rate limiting, account lockout, and session management.
"""

import asyncio
from datetime import datetime, timedelta

from auth import (
    SECURITY_CONFIG,
    AccountLockedError,
    RateLimitExceededError,
    WeakPasswordError,
    check_account_lockout,
    check_rate_limit,
    clear_failed_login_attempts,
    record_failed_login,
    should_refresh_token,
    validate_password_strength,
)


def test_password_strength_validation():
    """Test password strength validation rules."""
    print("\n=== Testing Password Strength Validation ===")

    test_cases = [
        # (password, should_pass, description)
        ("short", False, "Too short (< 12 chars)"),
        ("alllowercase123!", False, "No uppercase"),
        ("ALLUPPERCASE123!", False, "No lowercase"),
        ("NoDigitsHere!", False, "No digits"),
        ("NoSpecialChar123", False, "No special character"),
        ("password123!", False, "Common password"),
        ("Password123!", False, "Common password variant"),
        ("abc123Password!", False, "Sequential characters"),
        ("MySecureP@ssw0rd123", True, "Valid password"),
        ("C0mpl3x!P@ssw0rd", True, "Valid complex password"),
        ("Tr0ub4dor&3More", True, "Valid memorable password"),
    ]

    passed = 0
    failed = 0

    for password, should_pass, description in test_cases:
        is_valid, error_msg = validate_password_strength(password)

        if is_valid == should_pass:
            print(f"✓ {description}: '{password}' - {error_msg or 'PASSED'}")
            passed += 1
        else:
            print(f"✗ {description}: '{password}' - Expected {should_pass}, got {is_valid}")
            failed += 1

    print(f"\nPassword Validation: {passed} passed, {failed} failed")
    return failed == 0


def test_rate_limiting():
    """Test rate limiting for login attempts."""
    print("\n=== Testing Rate Limiting ===")

    email = f"ratelimit-test-{datetime.now().timestamp()}@example.com"
    max_attempts = SECURITY_CONFIG.max_login_attempts

    try:
        # Should allow up to max_attempts
        for i in range(max_attempts):
            check_rate_limit(email, "login")
            print(f"✓ Attempt {i+1}/{max_attempts} allowed")

        # Next attempt should fail
        try:
            check_rate_limit(email, "login")
            print("✗ Rate limit not enforced - should have raised exception")
            return False
        except RateLimitExceededError as e:
            print(f"✓ Rate limit enforced correctly: {e}")
            return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_account_lockout():
    """Test account lockout after failed login attempts."""
    print("\n=== Testing Account Lockout ===")

    email = f"lockout-test-{datetime.now().timestamp()}@example.com"
    max_failed = SECURITY_CONFIG.max_failed_attempts_before_lockout

    try:
        # Record failed login attempts
        for i in range(max_failed):
            record_failed_login(email)
            print(f"✓ Failed attempt {i+1}/{max_failed} recorded")

        # Should be locked now
        try:
            check_account_lockout(email)
            print("✗ Account lockout not enforced - should have raised exception")
            return False
        except AccountLockedError as e:
            print(f"✓ Account locked correctly: {e}")

        # Test clearing lockout
        clear_failed_login_attempts(email)
        check_account_lockout(email)  # Should not raise
        print("✓ Account lockout cleared successfully")

        return True

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_token_refresh_logic():
    """Test token refresh threshold logic."""
    print("\n=== Testing Token Refresh Logic ===")

    now = datetime.now()

    test_cases = [
        # (expires_at, should_refresh, description)
        ((now + timedelta(minutes=5)).isoformat(), True, "5 min until expiry - should refresh"),
        ((now + timedelta(minutes=9)).isoformat(), True, "9 min until expiry - should refresh"),
        ((now + timedelta(minutes=11)).isoformat(), False, "11 min until expiry - no refresh needed"),
        ((now + timedelta(hours=1)).isoformat(), False, "1 hour until expiry - no refresh needed"),
        ((now - timedelta(minutes=5)).isoformat(), False, "Already expired - no refresh needed"),
    ]

    passed = 0
    failed = 0

    for expires_at, expected, description in test_cases:
        result = should_refresh_token(expires_at)

        if result == expected:
            print(f"✓ {description} - Result: {result}")
            passed += 1
        else:
            print(f"✗ {description} - Expected {expected}, got {result}")
            failed += 1

    print(f"\nToken Refresh Logic: {passed} passed, {failed} failed")
    return failed == 0


async def test_signup_with_weak_password():
    """Test signup rejects weak passwords."""
    print("\n=== Testing Signup with Weak Password ===")

    from auth import signup_user

    weak_passwords = [
        "short",
        "password123",
        "NoSpecial123",
    ]

    for password in weak_passwords:
        try:
            await signup_user(
                email=f"test-{datetime.now().timestamp()}@example.com",
                password=password,
                name="Test User"
            )
            print(f"✗ Weak password '{password}' was accepted (should be rejected)")
            return False
        except WeakPasswordError as e:
            print(f"✓ Weak password '{password}' rejected: {e}")

    # Test with strong password (mock mode)
    try:
        result = await signup_user(
            email=f"test-{datetime.now().timestamp()}@example.com",
            password="MySecureP@ssw0rd123",
            name="Test User"
        )
        print(f"✓ Strong password accepted, user created: {result['user']['id']}")
        print(f"  Session expires: {result['session']['expires_at']}")
        print(f"  MFA enabled: {result['mfa_context']['enabled']}")
        return True
    except Exception as e:
        print(f"✗ Error with strong password: {e}")
        return False


async def test_login_with_rate_limiting():
    """Test login enforces rate limiting."""
    print("\n=== Testing Login with Rate Limiting ===")

    from auth import login_user

    email = f"login-test-{datetime.now().timestamp()}@example.com"

    # Create user first (mock mode)
    try:
        await signup_user(
            email=email,
            password="MySecureP@ssw0rd123",
            name="Test User"
        )
    except:
        pass  # May already exist

    # Attempt multiple logins
    for i in range(SECURITY_CONFIG.max_login_attempts):
        try:
            await login_user(email, "WrongPassword123!")
        except Exception:
            pass  # Expected to fail with wrong password
        print(f"✓ Login attempt {i+1} allowed")

    # Next attempt should hit rate limit
    try:
        await login_user(email, "WrongPassword123!")
        print("✗ Rate limit not enforced on login")
        return False
    except RateLimitExceededError as e:
        print(f"✓ Rate limit enforced on login: {e}")
        return True
    except Exception as e:
        print(f"  (Got expected auth error: {type(e).__name__})")
        # May hit rate limit or other error, check if rate limit was enforced


def test_security_configuration():
    """Test security configuration values."""
    print("\n=== Testing Security Configuration ===")

    print(f"Password Policy:")
    print(f"  Min length: {SECURITY_CONFIG.password_min_length} chars")
    print(f"  Require uppercase: {SECURITY_CONFIG.password_require_uppercase}")
    print(f"  Require lowercase: {SECURITY_CONFIG.password_require_lowercase}")
    print(f"  Require digit: {SECURITY_CONFIG.password_require_digit}")
    print(f"  Require special: {SECURITY_CONFIG.password_require_special}")

    print(f"\nRate Limiting:")
    print(f"  Max login attempts: {SECURITY_CONFIG.max_login_attempts}")
    print(f"  Max signup attempts: {SECURITY_CONFIG.max_signup_attempts}")
    print(f"  Window: {SECURITY_CONFIG.rate_limit_window_minutes} minutes")

    print(f"\nSession Management:")
    print(f"  Timeout: {SECURITY_CONFIG.session_timeout_hours} hour(s)")
    print(f"  Refresh threshold: {SECURITY_CONFIG.token_refresh_threshold_minutes} minutes")

    print(f"\nAccount Lockout:")
    print(f"  Max failed attempts: {SECURITY_CONFIG.max_failed_attempts_before_lockout}")
    print(f"  Lockout duration: {SECURITY_CONFIG.lockout_duration_minutes} minutes")

    # Verify configuration meets minimum security standards
    checks = [
        (SECURITY_CONFIG.password_min_length >= 12, "Password min length >= 12"),
        (SECURITY_CONFIG.max_login_attempts <= 10, "Login attempts limited"),
        (SECURITY_CONFIG.max_failed_attempts_before_lockout <= 10, "Failed attempts limited"),
        (SECURITY_CONFIG.session_timeout_hours >= 1, "Session timeout reasonable"),
    ]

    passed = all(check[0] for check in checks)
    for result, description in checks:
        print(f"{'✓' if result else '✗'} {description}")

    return passed


async def run_all_tests():
    """Run all security tests."""
    print("\n" + "="*60)
    print("AUTHENTICATION SECURITY TEST SUITE")
    print("="*60)

    results = []

    # Run synchronous tests
    results.append(("Security Configuration", test_security_configuration()))
    results.append(("Password Validation", test_password_strength_validation()))
    results.append(("Rate Limiting", test_rate_limiting()))
    results.append(("Account Lockout", test_account_lockout()))
    results.append(("Token Refresh Logic", test_token_refresh_logic()))

    # Run async tests
    results.append(("Signup Password Validation", await test_signup_with_weak_password()))
    results.append(("Login Rate Limiting", await test_login_with_rate_limiting()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)

    return passed == total


if __name__ == "__main__":
    import sys

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
