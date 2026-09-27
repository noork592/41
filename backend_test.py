#!/usr/bin/env python3
"""
Backend API Test Suite for Factory Order Management System
Tests OTP LOGIN two-step verification feature
"""

import requests
import json
import re
import subprocess
from typing import Dict, Any, Optional

# Backend URL from environment
BASE_URL = "https://app-clone-138.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def log_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def get_otp_from_logs(email: str, challenge_id: str) -> Optional[str]:
    """Extract OTP code from backend logs"""
    try:
        # Read backend error logs
        result = subprocess.run(
            ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            log_error(f"Failed to read backend logs: {result.stderr}")
            return None
        
        logs = result.stdout
        
        # Pattern: "Admin OTP for <email> (challenge <id>): <6-digit-code>"
        pattern = rf"Admin OTP for {re.escape(email)} \(challenge {re.escape(challenge_id)}\): (\d{{6}})"
        match = re.search(pattern, logs)
        
        if match:
            otp_code = match.group(1)
            log_info(f"Found OTP code in logs: {otp_code}")
            return otp_code
        else:
            log_warning(f"OTP code not found in logs for email={email}, challenge={challenge_id}")
            log_info(f"Log content:\n{logs[-500:]}")  # Show last 500 chars
            return None
            
    except Exception as e:
        log_error(f"Error reading logs: {e}")
        return None

def test_admin_login_no_otp():
    """Test 1: Admin login (otp_login=False) should return token directly"""
    print("\n" + "="*70)
    print("TEST 1: Admin login without OTP (otp_login=False)")
    print("="*70)
    
    payload = {
        "email": "admin",
        "password": "admin123"
    }
    
    log_info(f"POST {BASE_URL}/auth/login with username='admin'")
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    
    log_info(f"Status: {response.status_code}")
    log_info(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        log_error(f"Expected 200, got {response.status_code}")
        return None
    
    data = response.json()
    
    # Should NOT have otp_required
    if "otp_required" in data and data["otp_required"]:
        log_error("Admin has otp_login=False but got otp_required=True!")
        return None
    
    # Should have token
    if "token" not in data:
        log_error("Expected 'token' in response but not found")
        return None
    
    # Should have user object
    if "user" not in data:
        log_error("Expected 'user' in response but not found")
        return None
    
    user = data["user"]
    if user.get("role") != "admin":
        log_error(f"Expected role='admin', got {user.get('role')}")
        return None
    
    log_success("Admin login returned token directly (no OTP challenge)")
    log_success(f"User: {user.get('username')} ({user.get('email')}), role={user.get('role')}")
    
    return data["token"]

def test_enable_otp_for_user(admin_token: str):
    """Test 2: Enable OTP for 'user' account"""
    print("\n" + "="*70)
    print("TEST 2: Enable OTP for 'user' account")
    print("="*70)
    
    # First, get list of users to find 'user' id
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    log_info(f"GET {BASE_URL}/users")
    response = requests.get(f"{BASE_URL}/users", headers=headers)
    
    if response.status_code != 200:
        log_error(f"Failed to get users: {response.status_code}")
        return None
    
    users = response.json()
    user_account = None
    
    for u in users:
        if u.get("username") == "user":
            user_account = u
            break
    
    if not user_account:
        log_error("User account with username='user' not found")
        return None
    
    user_id = user_account["id"]
    log_info(f"Found user account: id={user_id}, email={user_account.get('email')}")
    log_info(f"Current otp_login status: {user_account.get('otp_login')}")
    
    # Enable OTP for this user
    log_info(f"PATCH {BASE_URL}/users/{user_id}/otp with otp_login=true")
    response = requests.patch(
        f"{BASE_URL}/users/{user_id}/otp",
        json={"otp_login": True},
        headers=headers
    )
    
    log_info(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        log_error(f"Failed to enable OTP: {response.status_code}")
        log_error(f"Response: {response.text}")
        return None
    
    updated_user = response.json()
    log_info(f"Response: {json.dumps(updated_user, indent=2)}")
    
    if not updated_user.get("otp_login"):
        log_error("OTP was not enabled for user")
        return None
    
    log_success(f"OTP enabled for user '{user_account.get('username')}'")
    return user_id

def test_user_login_with_otp():
    """Test 3: User login (otp_login=True) should return OTP challenge"""
    print("\n" + "="*70)
    print("TEST 3: User login with OTP enabled (should get challenge)")
    print("="*70)
    
    payload = {
        "email": "user",
        "password": "user123"
    }
    
    log_info(f"POST {BASE_URL}/auth/login with username='user'")
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    
    log_info(f"Status: {response.status_code}")
    log_info(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        log_error(f"Expected 200, got {response.status_code}")
        return None
    
    data = response.json()
    
    # Should have otp_required=True
    if not data.get("otp_required"):
        log_error("Expected otp_required=True but not found")
        log_error("BUG: User has otp_login=True but login returned token directly!")
        return None
    
    # Should have challenge_id
    if "challenge_id" not in data:
        log_error("Expected 'challenge_id' in response but not found")
        return None
    
    # Should NOT have token
    if "token" in data:
        log_error("Got 'token' in response but should only get OTP challenge")
        return None
    
    challenge_id = data["challenge_id"]
    sent_to = data.get("sent_to")
    email_sent = data.get("email_sent")
    
    log_success("User login returned OTP challenge (no token)")
    log_success(f"challenge_id: {challenge_id}")
    log_info(f"sent_to: {sent_to}")
    log_info(f"email_sent: {email_sent}")
    
    return challenge_id

def test_verify_otp(challenge_id: str, otp_code: str):
    """Test 4: Verify OTP with correct code"""
    print("\n" + "="*70)
    print("TEST 4: Verify OTP with correct code")
    print("="*70)
    
    payload = {
        "challenge_id": challenge_id,
        "code": otp_code
    }
    
    log_info(f"POST {BASE_URL}/auth/verify-otp")
    log_info(f"Payload: {json.dumps(payload, indent=2)}")
    response = requests.post(f"{BASE_URL}/auth/verify-otp", json=payload)
    
    log_info(f"Status: {response.status_code}")
    log_info(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        log_error(f"Expected 200, got {response.status_code}")
        return None
    
    data = response.json()
    
    # Should have token
    if "token" not in data:
        log_error("Expected 'token' in response but not found")
        return None
    
    # Should have user object
    if "user" not in data:
        log_error("Expected 'user' in response but not found")
        return None
    
    user = data["user"]
    
    log_success("OTP verification successful")
    log_success(f"Received JWT token: {data['token'][:20]}...")
    log_success(f"User: {user.get('username')} ({user.get('email')}), role={user.get('role')}")
    
    return data["token"]

def test_verify_otp_wrong_code(challenge_id: str):
    """Test 5: Verify OTP with incorrect code (negative test)"""
    print("\n" + "="*70)
    print("TEST 5: Verify OTP with incorrect code (negative test)")
    print("="*70)
    
    payload = {
        "challenge_id": challenge_id,
        "code": "000000"  # Wrong code
    }
    
    log_info(f"POST {BASE_URL}/auth/verify-otp with wrong code")
    response = requests.post(f"{BASE_URL}/auth/verify-otp", json=payload)
    
    log_info(f"Status: {response.status_code}")
    log_info(f"Response: {response.text}")
    
    if response.status_code != 401:
        log_error(f"Expected 401 for wrong OTP, got {response.status_code}")
        return False
    
    # Should NOT have token
    try:
        data = response.json()
        if "token" in data:
            log_error("Got token with wrong OTP code!")
            return False
    except:
        pass
    
    log_success("Wrong OTP correctly rejected with 401")
    return True

def test_disable_otp_for_user(admin_token: str, user_id: str):
    """Test 6: Disable OTP for user and verify direct login"""
    print("\n" + "="*70)
    print("TEST 6: Disable OTP and verify direct login")
    print("="*70)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Disable OTP
    log_info(f"PATCH {BASE_URL}/users/{user_id}/otp with otp_login=false")
    response = requests.patch(
        f"{BASE_URL}/users/{user_id}/otp",
        json={"otp_login": False},
        headers=headers
    )
    
    if response.status_code != 200:
        log_error(f"Failed to disable OTP: {response.status_code}")
        return False
    
    log_success("OTP disabled for user")
    
    # Now try login - should get token directly
    log_info("Attempting login with username='user' (should get token directly)")
    payload = {
        "email": "user",
        "password": "user123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    
    if response.status_code != 200:
        log_error(f"Login failed: {response.status_code}")
        return False
    
    data = response.json()
    
    # Should NOT have otp_required
    if data.get("otp_required"):
        log_error("User has otp_login=False but got OTP challenge!")
        return False
    
    # Should have token
    if "token" not in data:
        log_error("Expected token but not found")
        return False
    
    log_success("User login returned token directly (no OTP challenge)")
    return True

def main():
    print("\n" + "="*70)
    print("FACTORY ORDER MANAGEMENT - OTP LOGIN VERIFICATION TEST")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print("="*70)
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 6
    }
    
    # Test 1: Admin login without OTP
    admin_token = test_admin_login_no_otp()
    if admin_token:
        results["passed"] += 1
    else:
        results["failed"] += 1
        log_error("TEST 1 FAILED - Cannot continue")
        print_summary(results)
        return
    
    # Test 2: Enable OTP for user
    user_id = test_enable_otp_for_user(admin_token)
    if user_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        log_error("TEST 2 FAILED - Cannot continue")
        print_summary(results)
        return
    
    # Test 3: User login with OTP enabled
    challenge_id = test_user_login_with_otp()
    if challenge_id:
        results["passed"] += 1
    else:
        results["failed"] += 1
        log_error("TEST 3 FAILED - Cannot continue")
        print_summary(results)
        return
    
    # Test 4: Get OTP from logs and verify
    otp_code = get_otp_from_logs("user@factory.com", challenge_id)
    if not otp_code:
        log_error("Could not retrieve OTP from logs - Cannot continue")
        results["failed"] += 1
        print_summary(results)
        return
    
    user_token = test_verify_otp(challenge_id, otp_code)
    if user_token:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 5: Create new challenge for negative test
    log_info("\nCreating new OTP challenge for negative test...")
    challenge_id_2 = test_user_login_with_otp()
    if challenge_id_2:
        if test_verify_otp_wrong_code(challenge_id_2):
            results["passed"] += 1
        else:
            results["failed"] += 1
    else:
        log_error("Could not create challenge for negative test")
        results["failed"] += 1
    
    # Test 6: Disable OTP and verify direct login
    if test_disable_otp_for_user(admin_token, user_id):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    print_summary(results)

def print_summary(results: Dict[str, int]):
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {results['total']}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}{'='*70}")
        print("ALL TESTS PASSED ✓")
        print(f"{'='*70}{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}{'='*70}")
        print("SOME TESTS FAILED ✗")
        print(f"{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    main()
