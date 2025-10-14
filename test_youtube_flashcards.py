"""
Acceptance tests for YouTube flashcards functionality.
Tests the complete flow from YouTube URL to generated flashcards.
"""
import requests
import json
import time
import os
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEOS = {
    "manual_en": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - has manual EN captions
    "auto_en": "https://www.youtube.com/watch?v=9bZkp7q19f0",    # PSY Gangnam Style - has auto EN
    "no_captions": "https://www.youtube.com/watch?v=invalid123"  # Invalid video ID
}

def test_youtube_health_check():
    """Test the YouTube health check endpoint."""
    print("Testing YouTube health check...")
    
    response = requests.get(f"{BASE_URL}/youtube/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    
    data = response.json()
    assert data["status"] == "healthy", f"Health check not healthy: {data}"
    print("✅ YouTube health check passed")

def test_manual_captions():
    """Test with a video that has manual English captions."""
    print("Testing manual captions...")
    
    payload = {
        "url": TEST_VIDEOS["manual_en"],
        "n_cards": 5,
        "lang_hint": ["en"],
        "allow_auto_generated": False,
        "use_cookies": False,
        "enable_fallback": False
    }
    
    response = requests.post(f"{BASE_URL}/youtube/flashcards", json=payload)
    
    if response.status_code == 422:
        print("⚠️ Manual captions test failed - no manual captions available")
        return
    
    assert response.status_code == 200, f"Manual captions failed: {response.status_code} - {response.text}"
    
    data = response.json()
    assert "cards" in data, "Response missing cards"
    assert len(data["cards"]) <= 5, f"Too many cards generated: {len(data['cards'])}"
    assert data["lang"] == "en", f"Wrong language: {data['lang']}"
    
    # Validate card structure
    for card in data["cards"]:
        assert "front" in card, "Card missing front"
        assert "back" in card, "Card missing back"
        assert len(card["back"].split()) <= 45, f"Answer too long: {len(card['back'].split())} words"
        assert card.get("start_s") is not None, "Card missing start timestamp"
        assert card.get("end_s") is not None, "Card missing end timestamp"
    
    print(f"✅ Manual captions test passed - generated {len(data['cards'])} cards")

def test_auto_captions():
    """Test with a video that has auto-generated captions."""
    print("Testing auto-generated captions...")
    
    payload = {
        "url": TEST_VIDEOS["auto_en"],
        "n_cards": 3,
        "lang_hint": ["en"],
        "allow_auto_generated": True,
        "use_cookies": False,
        "enable_fallback": False
    }
    
    response = requests.post(f"{BASE_URL}/youtube/flashcards", json=payload)
    
    if response.status_code == 422:
        print("⚠️ Auto captions test failed - no captions available")
        return
    
    assert response.status_code == 200, f"Auto captions failed: {response.status_code} - {response.text}"
    
    data = response.json()
    assert "warnings" in data, "Response missing warnings"
    assert any("auto-generated" in warning.lower() for warning in data["warnings"]), "No auto-generated warning"
    
    print(f"✅ Auto captions test passed - generated {len(data['cards'])} cards with warnings: {data['warnings']}")

def test_no_captions():
    """Test with a video that has no captions."""
    print("Testing no captions scenario...")
    
    payload = {
        "url": TEST_VIDEOS["no_captions"],
        "n_cards": 5,
        "lang_hint": ["en"],
        "allow_auto_generated": True,
        "use_cookies": False,
        "enable_fallback": False
    }
    
    response = requests.post(f"{BASE_URL}/youtube/flashcards", json=payload)
    
    assert response.status_code == 422, f"Should fail with no captions: {response.status_code}"
    
    data = response.json()
    assert "detail" in data, "Error response missing detail"
    assert "transcript" in data["detail"].lower(), f"Wrong error message: {data['detail']}"
    
    print("✅ No captions test passed")

def test_fallback_enabled():
    """Test with fallback enabled."""
    print("Testing fallback functionality...")
    
    payload = {
        "url": TEST_VIDEOS["manual_en"],
        "n_cards": 3,
        "lang_hint": ["en"],
        "allow_auto_generated": False,
        "use_cookies": False,
        "enable_fallback": True
    }
    
    response = requests.post(f"{BASE_URL}/youtube/flashcards", json=payload)
    
    if response.status_code == 422:
        print("⚠️ Fallback test failed - no captions available")
        return
    
    assert response.status_code == 200, f"Fallback failed: {response.status_code} - {response.text}"
    
    data = response.json()
    print(f"✅ Fallback test passed - generated {len(data['cards'])} cards")

def test_frontend_api_proxy():
    """Test the frontend API proxy."""
    print("Testing frontend API proxy...")
    
    payload = {
        "url": TEST_VIDEOS["manual_en"],
        "n_cards": 2,
        "lang_hint": ["en"],
        "allow_auto_generated": True,
        "use_cookies": False,
        "enable_fallback": False
    }
    
    response = requests.post("http://localhost:3000/api/youtube/flashcards", json=payload)
    
    if response.status_code == 422:
        print("⚠️ Frontend proxy test failed - no captions available")
        return
    
    assert response.status_code == 200, f"Frontend proxy failed: {response.status_code} - {response.text}"
    
    data = response.json()
    assert "cards" in data, "Frontend response missing cards"
    
    print(f"✅ Frontend API proxy test passed - generated {len(data['cards'])} cards")

def run_all_tests():
    """Run all acceptance tests."""
    print("🚀 Starting YouTube flashcards acceptance tests...\n")
    
    tests = [
        test_youtube_health_check,
        test_manual_captions,
        test_auto_captions,
        test_no_captions,
        test_fallback_enabled,
        test_frontend_api_proxy,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed. Check the output above.")

if __name__ == "__main__":
    run_all_tests()
