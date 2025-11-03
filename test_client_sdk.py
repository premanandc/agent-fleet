#!/usr/bin/env python3
"""
Test Client for Router Agent using LangGraph SDK

This script uses the official LangGraph SDK to test the Router agent.
"""

import asyncio
from langgraph_sdk import get_client


async def test_router():
    """Run automated tests for Router Agent"""

    print("=" * 70)
    print("Router Agent Test Client (SDK)")
    print("=" * 70)

    # Create client
    client = get_client(url="http://localhost:2024")

    # Test 1: Quick validation
    print("\n🧪 TEST 1: Quick Validation (should use QuickAgent)")
    print("-" * 70)

    async for chunk in client.runs.stream(
        None,  # Threadless run
        "router",  # Assistant ID
        input={
            "messages": [{
                "role": "user",
                "content": "Can you quickly validate the syntax of my code?"
            }]
        },
        config={
            "configurable": {
                "mode": "auto"
            }
        },
        stream_mode="values"
    ):
        print(".", end="", flush=True)
        if chunk.data and "final_response" in chunk.data:
            print(f"\n\n📊 Result:\n{chunk.data['final_response']}")

    print("\n" + "=" * 70)

    # Test 2: Deep fix
    print("\n🧪 TEST 2: Deep Fix (should use SlowAgent)")
    print("-" * 70)

    async for chunk in client.runs.stream(
        None,
        "router",
        input={
            "messages": [{
                "role": "user",
                "content": "Fix all the SonarQube violations in my codebase"
            }]
        },
        config={
            "configurable": {
                "mode": "auto"
            }
        },
        stream_mode="values"
    ):
        print(".", end="", flush=True)
        if chunk.data and "final_response" in chunk.data:
            print(f"\n\n📊 Result:\n{chunk.data['final_response']}")

    print("\n" + "=" * 70)

    # Test 3: Parallel execution
    print("\n🧪 TEST 3: Parallel Execution (should use both agents)")
    print("-" * 70)

    async for chunk in client.runs.stream(
        None,
        "router",
        input={
            "messages": [{
                "role": "user",
                "content": "Quick check my code and then fix any SonarQube issues"
            }]
        },
        config={
            "configurable": {
                "mode": "auto"
            }
        },
        stream_mode="values"
    ):
        print(".", end="", flush=True)
        if chunk.data and "final_response" in chunk.data:
            print(f"\n\n📊 Result:\n{chunk.data['final_response']}")

    print("\n" + "=" * 70)
    print("✅ All tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_router())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
