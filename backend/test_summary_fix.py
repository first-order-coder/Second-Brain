"""
Test script to verify summary functionality fixes
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_get_empty_summary():
    """Test GET endpoint with non-existent source"""
    print("🔍 Testing GET endpoint with non-existent source...")
    try:
        response = requests.get(f"{BASE_URL}/summaries/non-existent-source")
        if response.status_code == 200:
            data = response.json()
            expected = {"summary_id": None, "source_id": "non-existent-source", "sentences": []}
            if data == expected:
                print("✅ GET endpoint handles non-existent source correctly")
                return True
            else:
                print(f"❌ GET endpoint returned unexpected data: {data}")
                return False
        else:
            print(f"❌ GET endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ GET endpoint error: {e}")
        return False

def test_refresh_non_existent():
    """Test refresh endpoint with non-existent source"""
    print("🔍 Testing refresh endpoint with non-existent source...")
    try:
        response = requests.post(f"{BASE_URL}/summaries/non-existent-source/refresh")
        if response.status_code == 404:
            print("✅ Refresh endpoint correctly returns 404 for non-existent source")
            return True
        else:
            print(f"❌ Refresh endpoint returned unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Refresh endpoint error: {e}")
        return False

def test_cors_options():
    """Test CORS preflight"""
    print("🔍 Testing CORS OPTIONS request...")
    try:
        response = requests.options(f"{BASE_URL}/summaries/test-source/refresh")
        if response.status_code == 200:
            print("✅ CORS OPTIONS request handled correctly")
            return True
        else:
            print(f"❌ CORS OPTIONS failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ CORS OPTIONS error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running summary functionality tests...\n")
    
    tests = [
        test_health_check,
        test_get_empty_summary,
        test_refresh_non_existent,
        test_cors_options
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Summary functionality is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
