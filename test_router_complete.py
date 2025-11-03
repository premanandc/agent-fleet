#!/usr/bin/env python3
"""
Complete Router Test Suite
"""

import asyncio
from langgraph_sdk import get_client


async def test_router_complete():
    """Test Router with multiple scenarios"""

    print("=" * 70)
    print("Router Agent Complete Test Suite")
    print("=" * 70)

    client = get_client(url="http://localhost:2024")

    # Test 1: Quick validation (should delegate to QuickAgent)
    print("\n🧪 TEST 1: Quick Validation Task")
    print("-" * 70)
    print("Request: 'Quick check my code for syntax errors'")

    try:
        result = await client.runs.wait(
            None,
            "router",
            input={
                "messages": [{
                    "role": "user",
                    "content": "Quick check my code for syntax errors"
                }]
            },
            config={"configurable": {"mode": "auto"}}
        )

        print(f"\n✓ Test 1 completed!")
        if "final_response" in result:
            print(f"\n📊 Response preview:\n{result['final_response'][:300]}...")

    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")

    # Test 2: Deep analysis (should delegate to SlowAgent)
    print("\n\n🧪 TEST 2: Deep Analysis Task")
    print("-" * 70)
    print("Request: 'Fix all SonarQube violations in my codebase'")

    try:
        result = await client.runs.wait(
            None,
            "router",
            input={
                "messages": [{
                    "role": "user",
                    "content": "Fix all SonarQube violations in my codebase"
                }]
            },
            config={"configurable": {"mode": "auto"}}
        )

        print(f"\n✓ Test 2 completed!")
        if "final_response" in result:
            print(f"\n📊 Response preview:\n{result['final_response'][:300]}...")

    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")

    # Test 3: Off-topic request (should be rejected)
    print("\n\n🧪 TEST 3: Off-topic Request (should be rejected)")
    print("-" * 70)
    print("Request: 'What's the weather like today?'")

    try:
        result = await client.runs.wait(
            None,
            "router",
            input={
                "messages": [{
                    "role": "user",
                    "content": "What's the weather like today?"
                }]
            },
            config={"configurable": {"mode": "auto"}}
        )

        print(f"\n✓ Test 3 completed!")
        if "final_response" in result:
            print(f"\n📊 Response:\n{result['final_response'][:300]}...")

    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")

    print("\n\n" + "=" * 70)
    print("✅ All tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_router_complete())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
