"""
Simplified security feature test - tests core functionality without external dependencies.
"""

from datetime import datetime, timedelta

from auth import (
    SECURITY_CONFIG,
    AccountLockedError,
    RateLimitExceededError,
    check_account_lockout,
    check_rate_limit,
    clear_failed_login_attempts,
    record_failed_login,
    should_refresh_token,
    validate_password_strength,
)


def main():
    print("\n" + "="*70)
    print("AUTHENTICATION SECURITY FEATURES TEST")
    print("="*70)

    all_passed = True

    # Test 1: Password Validation
    print("\n[TEST 1] Password Strength Validation")
    print("-" * 70)

    test_passwords = [
        ("Short1!", False, "Too short"),
        ("nouppercase123!", False, "Missing uppercase"),
        ("NOLOWERCASE123!", False, "Missing lowercase"),
        ("NoDigitsHere!", False, "Missing digit"),
        ("NoSpecialChar123", False, "Missing special char"),
        ("password", False, "Too common"),
        ("MySecureP@ssw0rd123", True, "Valid strong password"),
        ("C0mpl3x!P@ssw0rd", True, "Valid complex password"),
    ]

    for password, expected, desc in test_passwords:
        valid, error = validate_password_strength(password)
        status = "✓" if valid == expected else "✗"
        result = "VALID" if valid else error
        print(f"{status} {desc:30} | {password:25} | {result}")
        if valid != expected:
            all_passed = False

    # Test 2: Rate Limiting
    print("\n[TEST 2] Rate Limiting")
    print("-" * 70)

    email = f"test-{datetime.now().timestamp()}@example.com"

    try:
        for i in range(SECURITY_CONFIG.max_login_attempts):
            check_rate_limit(email, "login")
        print(f"✓ Allowed {SECURITY_CONFIG.max_login_attempts} attempts")

        try:
            check_rate_limit(email, "login")
            print("✗ Rate limit NOT enforced (should have blocked)")
            all_passed = False
        except RateLimitExceededError as e:
            print(f"✓ Rate limit enforced after {SECURITY_CONFIG.max_login_attempts} attempts")

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        all_passed = False

    # Test 3: Account Lockout
    print("\n[TEST 3] Account Lockout After Failed Logins")
    print("-" * 70)

    email2 = f"test-{datetime.now().timestamp() + 1}@example.com"

    try:
        for i in range(SECURITY_CONFIG.max_failed_attempts_before_lockout):
            record_failed_login(email2)
        print(f"✓ Recorded {SECURITY_CONFIG.max_failed_attempts_before_lockout} failed attempts")

        try:
            check_account_lockout(email2)
            print("✗ Account lockout NOT enforced (should have locked)")
            all_passed = False
        except AccountLockedError as e:
            print(f"✓ Account locked after {SECURITY_CONFIG.max_failed_attempts_before_lockout} failures")

        # Test clearing
        clear_failed_login_attempts(email2)
        check_account_lockout(email2)  # Should not raise
        print("✓ Account lockout successfully cleared")

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        all_passed = False

    # Test 4: Token Refresh Logic
    print("\n[TEST 4] Token Refresh Threshold")
    print("-" * 70)

    now = datetime.now()
    test_cases = [
        ((now + timedelta(minutes=5)).isoformat(), True, "5 min left"),
        ((now + timedelta(minutes=20)).isoformat(), False, "20 min left"),
        ((now + timedelta(hours=1)).isoformat(), False, "1 hour left"),
    ]

    for expires_at, expected, desc in test_cases:
        result = should_refresh_token(expires_at)
        status = "✓" if result == expected else "✗"
        action = "REFRESH" if result else "NO REFRESH"
        print(f"{status} {desc:20} | Should refresh: {action:15} | Expected: {expected}")
        if result != expected:
            all_passed = False

    # Summary
    print("\n" + "="*70)
    print("CONFIGURATION SUMMARY")
    print("="*70)
    print(f"Password min length:      {SECURITY_CONFIG.password_min_length} characters")
    print(f"Max login attempts:       {SECURITY_CONFIG.max_login_attempts} per {SECURITY_CONFIG.rate_limit_window_minutes} minutes")
    print(f"Max failed logins:        {SECURITY_CONFIG.max_failed_attempts_before_lockout} before lockout")
    print(f"Lockout duration:         {SECURITY_CONFIG.lockout_duration_minutes} minutes")
    print(f"Session timeout:          {SECURITY_CONFIG.session_timeout_hours} hour(s)")
    print(f"Token refresh threshold:  {SECURITY_CONFIG.token_refresh_threshold_minutes} minutes before expiry")

    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED - Security features working correctly!")
    else:
        print("✗ SOME TESTS FAILED - Review output above")
    print("="*70 + "\n")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
