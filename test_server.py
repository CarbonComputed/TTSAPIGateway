#!/usr/bin/env python3
"""
Test script for the TTS API Gateway
"""

import requests
import json
import time

BASE_URL = "http://localhost:5050"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return data.get('model_loaded', False)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:5050")
        return False

def test_voices():
    """Test the voices endpoint"""
    print("\nTesting voices endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/voices")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Voices endpoint: {data['count']} voices available")
            print(f"Available voices: {data['voices']}")
            return True
        else:
            print(f"❌ Voices endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Voices endpoint error: {e}")
        return False

def test_generate_audio():
    """Test the audio generation endpoint"""
    print("\nTesting audio generation...")
    
    test_cases = [
        {
            "text": "Hello, this is a test of the text-to-speech system.",
            "voice": "expr-voice-2-f"
        },
        {
            "text": "This is a longer test message to see how the system handles more text.",
            "voice": "expr-voice-3-m"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"Text: '{test_case['text']}'")
        print(f"Voice: {test_case['voice']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/generate",
                json=test_case,
                timeout=30  # 30 second timeout for audio generation
            )
            
            if response.status_code == 200:
                # Save the audio file
                filename = f"test_output_{i}_{test_case['voice']}.aac"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Audio generated successfully: {filename}")
                print(f"   File size: {len(response.content)} bytes")
            else:
                print(f"❌ Audio generation failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_error_handling():
    """Test error handling"""
    print("\nTesting error handling...")
    
    # Test missing text
    print("Testing missing text...")
    response = requests.post(f"{BASE_URL}/generate", json={"voice": "expr-voice-2-f"})
    if response.status_code == 400:
        print("✅ Correctly handled missing text")
    else:
        print(f"❌ Unexpected response for missing text: {response.status_code}")
    
    # Test invalid voice
    print("Testing invalid voice...")
    response = requests.post(f"{BASE_URL}/generate", json={"text": "test", "voice": "invalid-voice"})
    if response.status_code == 400:
        print("✅ Correctly handled invalid voice")
    else:
        print(f"❌ Unexpected response for invalid voice: {response.status_code}")
    
    # Test empty text
    print("Testing empty text...")
    response = requests.post(f"{BASE_URL}/generate", json={"text": "", "voice": "expr-voice-2-f"})
    if response.status_code == 400:
        print("✅ Correctly handled empty text")
    else:
        print(f"❌ Unexpected response for empty text: {response.status_code}")

def main():
    """Run all tests"""
    print("🚀 Starting TTS API Gateway tests...")
    print("=" * 50)
    
    # Test health first
    model_loaded = test_health()
    
    if not model_loaded:
        print("\n⚠️  Model not loaded. Some tests may fail.")
    
    # Test other endpoints
    test_voices()
    
    if model_loaded:
        test_generate_audio()
    else:
        print("\n⏭️  Skipping audio generation test (model not loaded)")
    
    test_error_handling()
    
    print("\n" + "=" * 50)
    print("🏁 Tests completed!")

if __name__ == "__main__":
    main() 