#!/usr/bin/env python3
"""
Backend API Test Suite for Factory ERP - Railway Crossing Avoidance + Flyover CRUD
Tests the fix for "Avoid railway crossing" and the new "Mark flyover" feature
"""

import requests
import json
import subprocess
from typing import Dict, Any, Optional, List

# Backend URL from environment
BASE_URL = "https://app-preview-3333.preview.emergentagent.com/api"

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

def check_backend_logs():
    """Check backend logs for errors"""
    try:
        result = subprocess.run(
            ["bash", "-c", "tail -n 100 /var/log/supervisor/backend.*.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            logs = result.stdout
            # Check for critical errors related to railway crossing functions
            error_keywords = [
                "Traceback",
                "_build_avoidance_route",
                "_crossings_on",
                "_rail_line_hits",
                "_fetch_railway_features",
                "create_flyover",
                "Exception in"
            ]
            
            found_errors = False
            for keyword in error_keywords:
                if keyword in logs:
                    found_errors = True
                    break
            
            if found_errors:
                log_warning("Found relevant errors in backend logs:")
                lines = logs.split('\n')
                for line in lines[-30:]:
                    if line.strip():
                        print(f"  {line}")
                return logs
        return None
    except Exception as e:
        log_warning(f"Could not read backend logs: {e}")
        return None

def test_health_endpoint():
    """Test 0: Health endpoint"""
    print("\n" + "="*70)
    print("TEST 0: Health Endpoint")
    print("="*70)
    
    try:
        log_info(f"GET {BASE_URL.replace('/api', '')}/health")
        response = requests.get(f"{BASE_URL.replace('/api', '')}/health", timeout=10)
        
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            log_success("Health endpoint returned 200")
            return True
        else:
            log_error(f"Health endpoint returned {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Health endpoint failed: {e}")
        return False

def test_admin_login():
    """Test 1: Admin login to get auth token"""
    print("\n" + "="*70)
    print("TEST 1: Admin Login")
    print("="*70)
    
    payload = {
        "email": "admin",
        "password": "admin123"
    }
    
    log_info(f"POST {BASE_URL}/auth/login")
    log_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=10)
        
        log_info(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            log_error(f"Login failed with status {response.status_code}")
            log_error(f"Response: {response.text}")
            check_backend_logs()
            return None
        
        data = response.json()
        
        if "token" not in data:
            log_error("No token in response")
            return None
        
        token = data["token"]
        log_success(f"Login successful, token: {token[:20]}...")
        
        return token
        
    except Exception as e:
        log_error(f"Login request failed: {e}")
        check_backend_logs()
        return None

def test_flyover_crud(token: str):
    """Test 2: Flyover CRUD endpoints"""
    print("\n" + "="*70)
    print("TEST 2: Flyover CRUD Endpoints")
    print("="*70)
    
    headers = {"Authorization": f"Bearer {token}"}
    all_passed = True
    created_ids = []
    
    # Test 2.1: GET /api/flyovers (initial state)
    print(f"\n{'-'*70}")
    log_info("Test 2.1: GET /api/flyovers (initial state)")
    print(f"{'-'*70}")
    
    try:
        response = requests.get(f"{BASE_URL}/flyovers", headers=headers, timeout=10)
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log_success(f"GET /api/flyovers returned 200, found {len(data)} existing flyovers")
            initial_count = len(data)
        else:
            log_error(f"GET /api/flyovers failed with status {response.status_code}")
            all_passed = False
            return all_passed, []
    except Exception as e:
        log_error(f"GET /api/flyovers failed: {e}")
        all_passed = False
        return all_passed, []
    
    # Test 2.2: POST /api/flyovers (create valid flyover)
    print(f"\n{'-'*70}")
    log_info("Test 2.2: POST /api/flyovers (create valid flyover)")
    print(f"{'-'*70}")
    
    test_flyover = {
        "lat": 30.9019,
        "lng": 75.8543
    }
    
    try:
        log_info(f"POST {BASE_URL}/flyovers")
        log_info(f"Payload: {json.dumps(test_flyover, indent=2)}")
        
        response = requests.post(f"{BASE_URL}/flyovers", json=test_flyover, headers=headers, timeout=10)
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log_info(f"Response: {json.dumps(data, indent=2)}")
            
            # Verify response structure
            if "id" in data and "lat" in data and "lng" in data and "label" in data:
                log_success(f"Flyover created successfully with id: {data['id']}")
                
                # Verify values
                if abs(data["lat"] - test_flyover["lat"]) < 0.0001 and abs(data["lng"] - test_flyover["lng"]) < 0.0001:
                    log_success("Coordinates match")
                else:
                    log_error(f"Coordinates mismatch: expected ({test_flyover['lat']}, {test_flyover['lng']}), got ({data['lat']}, {data['lng']})")
                    all_passed = False
                
                if data["label"] == "Flyover":
                    log_success("Default label 'Flyover' applied correctly")
                else:
                    log_warning(f"Label is '{data['label']}' instead of 'Flyover'")
                
                created_ids.append(data["id"])
            else:
                log_error("Response missing required fields (id, lat, lng, label)")
                all_passed = False
        else:
            log_error(f"POST /api/flyovers failed with status {response.status_code}")
            log_error(f"Response: {response.text}")
            all_passed = False
    except Exception as e:
        log_error(f"POST /api/flyovers failed: {e}")
        all_passed = False
    
    # Test 2.3: GET /api/flyovers (verify new flyover is present)
    print(f"\n{'-'*70}")
    log_info("Test 2.3: GET /api/flyovers (verify new flyover is present)")
    print(f"{'-'*70}")
    
    try:
        response = requests.get(f"{BASE_URL}/flyovers", headers=headers, timeout=10)
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log_success(f"GET /api/flyovers returned {len(data)} flyovers")
            
            if len(data) == initial_count + 1:
                log_success(f"Flyover count increased from {initial_count} to {len(data)}")
            else:
                log_warning(f"Expected {initial_count + 1} flyovers, got {len(data)}")
            
            # Verify our flyover is in the list
            if created_ids:
                found = any(f.get("id") == created_ids[0] for f in data)
                if found:
                    log_success("New flyover found in list")
                else:
                    log_error("New flyover NOT found in list")
                    all_passed = False
        else:
            log_error(f"GET /api/flyovers failed with status {response.status_code}")
            all_passed = False
    except Exception as e:
        log_error(f"GET /api/flyovers failed: {e}")
        all_passed = False
    
    # Test 2.4: POST /api/flyovers (invalid coordinates - should return 400)
    print(f"\n{'-'*70}")
    log_info("Test 2.4: POST /api/flyovers (invalid coordinates - should return 400)")
    print(f"{'-'*70}")
    
    invalid_flyover = {
        "lat": 200,  # Invalid latitude
        "lng": 0
    }
    
    try:
        log_info(f"POST {BASE_URL}/flyovers")
        log_info(f"Payload: {json.dumps(invalid_flyover, indent=2)}")
        
        response = requests.post(f"{BASE_URL}/flyovers", json=invalid_flyover, headers=headers, timeout=10)
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 400:
            log_success("Invalid coordinates correctly rejected with 400")
        else:
            log_error(f"Expected 400 for invalid coordinates, got {response.status_code}")
            all_passed = False
    except Exception as e:
        log_error(f"POST /api/flyovers with invalid coords failed: {e}")
        all_passed = False
    
    # Test 2.5: DELETE /api/flyovers/{id}
    print(f"\n{'-'*70}")
    log_info("Test 2.5: DELETE /api/flyovers/{id}")
    print(f"{'-'*70}")
    
    if created_ids:
        try:
            flyover_id = created_ids[0]
            log_info(f"DELETE {BASE_URL}/flyovers/{flyover_id}")
            
            response = requests.delete(f"{BASE_URL}/flyovers/{flyover_id}", headers=headers, timeout=10)
            log_info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") == True:
                    log_success(f"Flyover {flyover_id} deleted successfully")
                    created_ids.remove(flyover_id)
                else:
                    log_error(f"DELETE returned 200 but ok != true: {data}")
                    all_passed = False
            else:
                log_error(f"DELETE /api/flyovers/{flyover_id} failed with status {response.status_code}")
                all_passed = False
        except Exception as e:
            log_error(f"DELETE /api/flyovers failed: {e}")
            all_passed = False
    
    # Test 2.6: GET /api/flyovers (verify flyover is gone)
    print(f"\n{'-'*70}")
    log_info("Test 2.6: GET /api/flyovers (verify flyover is gone)")
    print(f"{'-'*70}")
    
    try:
        response = requests.get(f"{BASE_URL}/flyovers", headers=headers, timeout=10)
        log_info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log_success(f"GET /api/flyovers returned {len(data)} flyovers")
            
            if len(data) == initial_count:
                log_success(f"Flyover count back to initial {initial_count}")
            else:
                log_warning(f"Expected {initial_count} flyovers, got {len(data)}")
        else:
            log_error(f"GET /api/flyovers failed with status {response.status_code}")
            all_passed = False
    except Exception as e:
        log_error(f"GET /api/flyovers failed: {e}")
        all_passed = False
    
    return all_passed, created_ids

def test_optimize_baseline(token: str):
    """Test 3: Baseline optimize (before adding flyovers)"""
    print("\n" + "="*70)
    print("TEST 3: Baseline Optimize (Record C_before)")
    print("="*70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Use the exact stops from the review request
    payload = {
        "stops": [
            {"lat": 30.905, "lng": 75.862, "name": "Stop A"},
            {"lat": 30.898, "lng": 75.858, "name": "Stop B"}
        ]
    }
    
    log_info(f"POST {BASE_URL}/transport/optimize")
    log_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/transport/optimize",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        log_info(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            log_error(f"Optimize failed with status {response.status_code}")
            log_error(f"Response: {response.text}")
            check_backend_logs()
            return None
        
        data = response.json()
        
        # Verify response structure
        if "options" not in data:
            log_error("No 'options' array in response")
            return None
        
        options = data["options"]
        log_success(f"Received {len(options)} route options")
        
        # Print detailed table
        print(f"\n{'Label':<30} {'Distance (km)':<15} {'Crossings':<12} {'Order':<15} {'Geometry len':<15}")
        print("-" * 87)
        
        avoid_option = None
        shortest_option = None
        
        for opt in options:
            label = opt.get("label", "Unknown")
            distance = opt.get("total_distance_km")
            crossings = opt.get("crossings")
            order = opt.get("order", [])
            geometry = opt.get("geometry", "")
            
            dist_str = f"{distance:.2f}" if distance is not None else "N/A"
            cross_str = str(crossings) if crossings is not None else "null"
            order_str = str(order)
            geom_str = str(len(geometry))
            
            print(f"{label:<30} {dist_str:<15} {cross_str:<12} {order_str:<15} {geom_str:<15}")
            
            if label == "Avoid railway crossing":
                avoid_option = opt
            elif label == "Shortest (optimized)":
                shortest_option = opt
        
        print("-" * 87)
        
        # Verify "Avoid railway crossing" option is present
        if not avoid_option:
            log_error("'Avoid railway crossing' option NOT present")
            log_warning("This may indicate external services are unreachable")
            return None
        
        log_success("'Avoid railway crossing' option is present")
        
        # Verify crossings field
        if "crossings" not in avoid_option:
            log_error("'Avoid railway crossing' option missing 'crossings' field")
            return None
        
        c_before = avoid_option["crossings"]
        
        if c_before is None:
            log_warning("'Avoid railway crossing' option has null crossings (external services may be unreachable)")
            return None
        
        log_success(f"C_before (Avoid railway crossing crossings): {c_before}")
        
        # Also record shortest option crossings
        if shortest_option and shortest_option.get("crossings") is not None:
            log_info(f"Shortest option crossings: {shortest_option['crossings']}")
        
        return {
            "c_before": c_before,
            "avoid_option": avoid_option,
            "shortest_option": shortest_option,
            "all_options": options
        }
        
    except Exception as e:
        log_error(f"Optimize request failed: {e}")
        check_backend_logs()
        return None

def test_optimize_with_flyovers(token: str, baseline_data: Dict):
    """Test 4: KEY TEST - Create flyovers and verify crossings decrease"""
    print("\n" + "="*70)
    print("TEST 4: KEY TEST - User Flyovers Reduce Crossings")
    print("="*70)
    
    headers = {"Authorization": f"Bearer {token}"}
    created_flyover_ids = []
    
    c_before = baseline_data["c_before"]
    log_info(f"Baseline crossings (C_before): {c_before}")
    
    # Create flyovers at the crossing points
    # The review request mentions user-marked phataks around lat 30.902, lng 75.854
    # We'll create flyovers at these strategic points to cover both legs' crossings
    flyover_points = [
        {"lat": 30.9040, "lng": 75.8548, "name": "Flyover 1"},
        {"lat": 30.8990, "lng": 75.8555, "name": "Flyover 2"},
        {"lat": 30.90191, "lng": 75.85429, "name": "Flyover 3"},
        {"lat": 30.89965, "lng": 75.85309, "name": "Flyover 4"}
    ]
    
    print(f"\n{'-'*70}")
    log_info("Step 1: Creating flyovers at crossing points")
    print(f"{'-'*70}")
    
    for i, point in enumerate(flyover_points):
        try:
            payload = {"lat": point["lat"], "lng": point["lng"]}
            log_info(f"Creating flyover {i+1}/4 at ({point['lat']}, {point['lng']})")
            
            response = requests.post(f"{BASE_URL}/flyovers", json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                created_flyover_ids.append(data["id"])
                log_success(f"Flyover {i+1} created with id: {data['id']}")
            else:
                log_error(f"Failed to create flyover {i+1}: status {response.status_code}")
                log_error(f"Response: {response.text}")
        except Exception as e:
            log_error(f"Failed to create flyover {i+1}: {e}")
    
    if len(created_flyover_ids) != len(flyover_points):
        log_error(f"Only created {len(created_flyover_ids)}/{len(flyover_points)} flyovers")
    else:
        log_success(f"All {len(flyover_points)} flyovers created successfully")
    
    # Now call optimize again with the SAME stops
    print(f"\n{'-'*70}")
    log_info("Step 2: Calling optimize with same stops (after adding flyovers)")
    print(f"{'-'*70}")
    
    payload = {
        "stops": [
            {"lat": 30.905, "lng": 75.862, "name": "Stop A"},
            {"lat": 30.898, "lng": 75.858, "name": "Stop B"}
        ]
    }
    
    log_info(f"POST {BASE_URL}/transport/optimize")
    
    try:
        response = requests.post(
            f"{BASE_URL}/transport/optimize",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        log_info(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            log_error(f"Optimize failed with status {response.status_code}")
            log_error(f"Response: {response.text}")
            check_backend_logs()
            return False, created_flyover_ids
        
        data = response.json()
        
        if "options" not in data:
            log_error("No 'options' array in response")
            return False, created_flyover_ids
        
        options = data["options"]
        log_success(f"Received {len(options)} route options")
        
        # Print detailed table
        print(f"\n{'Label':<30} {'Distance (km)':<15} {'Crossings':<12} {'Order':<15} {'Geometry len':<15}")
        print("-" * 87)
        
        avoid_option = None
        
        for opt in options:
            label = opt.get("label", "Unknown")
            distance = opt.get("total_distance_km")
            crossings = opt.get("crossings")
            order = opt.get("order", [])
            geometry = opt.get("geometry", "")
            
            dist_str = f"{distance:.2f}" if distance is not None else "N/A"
            cross_str = str(crossings) if crossings is not None else "null"
            order_str = str(order)
            geom_str = str(len(geometry))
            
            print(f"{label:<30} {dist_str:<15} {cross_str:<12} {order_str:<15} {geom_str:<15}")
            
            if label == "Avoid railway crossing":
                avoid_option = opt
        
        print("-" * 87)
        
        # Verify "Avoid railway crossing" option is present
        if not avoid_option:
            log_error("'Avoid railway crossing' option NOT present after adding flyovers")
            return False, created_flyover_ids
        
        log_success("'Avoid railway crossing' option is present")
        
        # Get C_after
        c_after = avoid_option.get("crossings")
        
        if c_after is None:
            log_error("'Avoid railway crossing' option has null crossings")
            return False, created_flyover_ids
        
        log_success(f"C_after (Avoid railway crossing crossings): {c_after}")
        
        # THE KEY VERIFICATION: C_after < C_before
        print(f"\n{'-'*70}")
        log_info("Step 3: Verifying crossings reduction")
        print(f"{'-'*70}")
        
        log_info(f"C_before: {c_before}")
        log_info(f"C_after:  {c_after}")
        log_info(f"Reduction: {c_before - c_after}")
        
        if c_after < c_before:
            log_success(f"✓✓ PASS: C_after ({c_after}) < C_before ({c_before})")
            log_success(f"User-marked flyovers successfully reduced crossings by {c_before - c_after}")
            return True, created_flyover_ids
        elif c_after == c_before:
            log_error(f"✗✗ FAIL: C_after ({c_after}) == C_before ({c_before})")
            log_error("User-marked flyovers did NOT reduce crossings")
            log_error("The flyovers are not being honored by the avoidance route")
            return False, created_flyover_ids
        else:
            log_error(f"✗✗ FAIL: C_after ({c_after}) > C_before ({c_before})")
            log_error("Crossings INCREASED after adding flyovers (unexpected)")
            return False, created_flyover_ids
        
    except Exception as e:
        log_error(f"Optimize request failed: {e}")
        check_backend_logs()
        return False, created_flyover_ids

def cleanup_flyovers(token: str, flyover_ids: List[str]):
    """Cleanup: Delete all test flyovers"""
    print("\n" + "="*70)
    print("CLEANUP: Deleting Test Flyovers")
    print("="*70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if not flyover_ids:
        log_info("No flyovers to clean up")
        return True
    
    log_info(f"Deleting {len(flyover_ids)} test flyovers...")
    
    all_deleted = True
    for i, flyover_id in enumerate(flyover_ids):
        try:
            log_info(f"Deleting flyover {i+1}/{len(flyover_ids)}: {flyover_id}")
            response = requests.delete(f"{BASE_URL}/flyovers/{flyover_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                log_success(f"Flyover {flyover_id} deleted")
            else:
                log_error(f"Failed to delete flyover {flyover_id}: status {response.status_code}")
                all_deleted = False
        except Exception as e:
            log_error(f"Failed to delete flyover {flyover_id}: {e}")
            all_deleted = False
    
    # Verify all flyovers are gone
    try:
        response = requests.get(f"{BASE_URL}/flyovers", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            remaining_test_flyovers = [f for f in data if f.get("id") in flyover_ids]
            
            if not remaining_test_flyovers:
                log_success("All test flyovers successfully removed")
            else:
                log_error(f"{len(remaining_test_flyovers)} test flyovers still present")
                all_deleted = False
    except Exception as e:
        log_warning(f"Could not verify cleanup: {e}")
    
    return all_deleted

def main():
    print("\n" + "="*70)
    print("FACTORY ERP - RAILWAY CROSSING AVOIDANCE + FLYOVER CRUD TEST")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print("="*70)
    
    results = {
        "passed": 0,
        "failed": 0,
        "critical_failure": False
    }
    
    # Test 0: Health check
    print("\n")
    if test_health_endpoint():
        results["passed"] += 1
    else:
        results["failed"] += 1
        log_warning("Health check failed but continuing with tests...")
    
    # Test 1: Admin login
    token = test_admin_login()
    if not token:
        results["failed"] += 1
        results["critical_failure"] = True
        log_error("Cannot continue without auth token")
        print_summary(results)
        return
    
    results["passed"] += 1
    
    # Test 2: Flyover CRUD
    crud_passed, leftover_ids = test_flyover_crud(token)
    if crud_passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Clean up any leftover flyovers from CRUD test
    if leftover_ids:
        cleanup_flyovers(token, leftover_ids)
    
    # Test 3: Baseline optimize (record C_before)
    baseline_data = test_optimize_baseline(token)
    if baseline_data:
        results["passed"] += 1
    else:
        results["failed"] += 1
        results["critical_failure"] = True
        log_error("Cannot continue without baseline data")
        print_summary(results)
        return
    
    # Test 4: KEY TEST - Optimize with flyovers (verify C_after < C_before)
    key_test_passed, flyover_ids = test_optimize_with_flyovers(token, baseline_data)
    if key_test_passed:
        results["passed"] += 1
        log_success("✓✓ KEY TEST PASSED: User flyovers reduce crossings")
    else:
        results["failed"] += 1
        log_error("✗✗ KEY TEST FAILED: User flyovers did NOT reduce crossings")
    
    # Cleanup: Delete all test flyovers
    cleanup_success = cleanup_flyovers(token, flyover_ids)
    if cleanup_success:
        results["passed"] += 1
    else:
        results["failed"] += 1
        log_warning("Cleanup incomplete - some test flyovers may remain")
    
    # Check backend logs for errors
    print("\n" + "="*70)
    print("STABILITY CHECK: Backend Logs")
    print("="*70)
    
    logs = check_backend_logs()
    if logs:
        log_warning("Found errors/exceptions in backend logs (see above)")
        results["failed"] += 1
    else:
        log_success("No critical errors found in backend logs")
        results["passed"] += 1
    
    print_summary(results, key_test_passed)

def print_summary(results: Dict[str, int], key_test_passed: bool = False):
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {Colors.GREEN}{results['passed']}{Colors.END}")
    print(f"Failed: {Colors.RED}{results['failed']}{Colors.END}")
    
    if results.get("critical_failure"):
        print(f"\n{Colors.RED}{'='*70}")
        print("CRITICAL FAILURE - TESTS COULD NOT COMPLETE")
        print(f"{'='*70}{Colors.END}\n")
    elif results['failed'] == 0:
        print(f"\n{Colors.GREEN}{'='*70}")
        print("ALL TESTS PASSED ✓✓")
        print(f"{'='*70}{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}{'='*70}")
        print("SOME TESTS FAILED")
        if not key_test_passed:
            print(f"{Colors.RED}KEY TEST FAILED: User flyovers NOT reducing crossings{Colors.END}")
        print(f"{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    main()
