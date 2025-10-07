#!/usr/bin/env python3
"""Test script to isolate OpenAI client initialization issue"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_openai_client():
    """Test OpenAI client initialization"""
    print("Testing OpenAI client initialization...")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    
    try:
        # Test 1: Basic initialization
        print("\nTest 1: Basic OpenAI client initialization")
        client = OpenAI(api_key=api_key)
        print("✅ Basic initialization successful")
        
        # Test 2: Check client properties
        print(f"Client type: {type(client)}")
        print(f"Client has chat: {hasattr(client, 'chat')}")
        
        # Test 3: Simple API call
        print("\nTest 2: Simple API call")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, respond with just 'Hi'"}],
            max_tokens=10
        )
        print(f"✅ API call successful: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_openai_client()
