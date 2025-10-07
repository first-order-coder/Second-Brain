#!/usr/bin/env python3
"""
Simple test script to verify the API endpoints work correctly.
Run this after starting the backend server.
"""

import requests
import json
import os
import time

BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    print("🧪 Testing PDF to Flashcards API")
    print("=" * 50)
    
    # Test 1: Check if API is running
    print("1. Testing API health...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API is running")
        else:
            print("❌ API returned unexpected status:", response.status_code)
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure backend is running on port 8000")
        return
    
    # Test 2: Create a simple test PDF content (simulated)
    print("\n2. Testing flashcard generation...")
    
    # Note: This test requires a real PDF file
    # For a complete test, you would need to:
    # 1. Create or find a test PDF file
    # 2. Upload it via the /upload-pdf endpoint
    # 3. Start flashcard generation
    # 4. Poll for completion
    # 5. Retrieve and verify flashcards
    
    print("⚠️  To test PDF upload and flashcard generation:")
    print("   - Create a test PDF file")
    print("   - Use the web interface at http://localhost:3000")
    print("   - Or use curl commands:")
    print()
    print("   curl -X POST 'http://localhost:8000/upload-pdf' \\")
    print("     -H 'Content-Type: multipart/form-data' \\")
    print("     -F 'file=@test.pdf'")
    print()
    
    # Test 3: Check environment variables
    print("3. Checking environment setup...")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        if api_key.startswith("sk-"):
            print("✅ OpenAI API key is set")
        else:
            print("⚠️  OpenAI API key doesn't look correct (should start with 'sk-')")
    else:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Set it in your .env file or environment")
    
    print("\n🎉 Basic API tests completed!")
    print("\nNext steps:")
    print("1. Make sure your OpenAI API key is set")
    print("2. Start the frontend: npm run dev (in frontend/ directory)")
    print("3. Visit http://localhost:3000")
    print("4. Upload a test PDF file")

def test_with_sample_pdf():
    """Test with a real PDF file if available"""
    print("\n📄 Testing with sample PDF...")
    
    # Look for common test PDFs
    test_files = ["test.pdf", "sample.pdf", "document.pdf"]
    test_file = None
    
    for file in test_files:
        if os.path.exists(file):
            test_file = file
            break
    
    if not test_file:
        print("⚠️  No test PDF found. Create a test.pdf file to run this test.")
        return
    
    print(f"Found test file: {test_file}")
    
    try:
        # Upload PDF
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/upload-pdf", files=files)
        
        if response.status_code == 200:
            data = response.json()
            pdf_id = data['pdf_id']
            print(f"✅ PDF uploaded successfully. ID: {pdf_id}")
            
            # Start flashcard generation
            response = requests.post(f"{BASE_URL}/generate-flashcards/{pdf_id}")
            if response.status_code == 200:
                print("✅ Flashcard generation started")
                
                # Poll for completion
                print("⏳ Waiting for processing...")
                while True:
                    time.sleep(2)
                    response = requests.get(f"{BASE_URL}/status/{pdf_id}")
                    status_data = response.json()
                    
                    if status_data['status'] == 'completed':
                        print("✅ Processing completed!")
                        
                        # Get flashcards
                        response = requests.get(f"{BASE_URL}/flashcards/{pdf_id}")
                        flashcard_data = response.json()
                        
                        print(f"📚 Generated {len(flashcard_data['flashcards'])} flashcards")
                        
                        # Show first flashcard
                        if flashcard_data['flashcards']:
                            first_card = flashcard_data['flashcards'][0]
                            print(f"\nSample flashcard:")
                            print(f"Q: {first_card['question']}")
                            print(f"A: {first_card['answer']}")
                        
                        break
                    elif status_data['status'] == 'error':
                        print("❌ Processing failed")
                        break
                    else:
                        print(f"⏳ Status: {status_data['status']}")
                        
            else:
                print("❌ Failed to start flashcard generation")
        else:
            print("❌ Failed to upload PDF")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_api_endpoints()
    
    # Uncomment the line below to test with a real PDF file
    # test_with_sample_pdf()
