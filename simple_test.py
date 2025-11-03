#!/usr/bin/env python3
"""
Simple test to invoke agents directly without using /assistants/search
"""

import requests
import json

BASE_URL = "http://localhost:2024"

print("=" * 70)
print("Simple Agent Test")
print("=" * 70)

# Test 1: Invoke QuickAgent directly
print("\n1. Testing QuickAgent directly...")
print("-" * 70)

try:
    # Create a thread for quick_agent
    response = requests.post(
        f"{BASE_URL}/threads",
        json={
            "input": {
                "messages": [
                    {"role": "user", "content": "Quick check my code"}
                ]
            },
            "assistant_id": "quick_agent",
            "stream_mode": ["values"]
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ QuickAgent responded")
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, 'content'):
                    print(f"\nResponse: {msg.content[:200]}...")
                elif isinstance(msg, dict) and 'content' in msg:
                    print(f"\nResponse: {msg['content'][:200]}...")
    else:
        print(f"✗ Error: {response.text[:500]}")

except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Invoke SlowAgent directly
print("\n\n2. Testing SlowAgent directly...")
print("-" * 70)

try:
    response = requests.post(
        f"{BASE_URL}/threads",
        json={
            "input": {
                "messages": [
                    {"role": "user", "content": "Fix SonarQube violations"}
                ]
            },
            "assistant_id": "slow_agent",
            "stream_mode": ["values"]
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ SlowAgent responded")
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, 'content'):
                    print(f"\nResponse: {msg.content[:200]}...")
                elif isinstance(msg, dict) and 'content' in msg:
                    print(f"\nResponse: {msg['content'][:200]}...")
    else:
        print(f"✗ Error: {response.text[:500]}")

except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Try to invoke Router
print("\n\n3. Testing Router...")
print("-" * 70)

try:
    response = requests.post(
        f"{BASE_URL}/threads",
        json={
            "input": {
                "messages": [
                    {"role": "user", "content": "Quick check my code"}
                ]
            },
            "assistant_id": "router",
            "stream_mode": ["values"]
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Router responded")
        print(f"\nResult keys: {list(result.keys())}")
        if "final_response" in result:
            print(f"\nFinal Response: {result['final_response']}")
    else:
        print(f"✗ Error: {response.text[:1000]}")

except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 70)
print("Test Complete")
print("=" * 70)
