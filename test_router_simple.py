#!/usr/bin/env python3
"""
Simple Router Test using create/wait instead of stream
"""

import asyncio
from langgraph_sdk import get_client


async def test_router_simple():
    """Test Router using create + wait"""

    print("=" * 70)
    print("Router Agent Simple Test (create/wait)")
    print("=" * 70)

    # Create client
    client = get_client(url="http://localhost:2024")

    # Test 1: Quick validation
    print("\n🧪 TEST 1: Quick Validation (should use QuickAgent)")
    print("-" * 70)

    try:
        # Create a run and wait for it to complete
        result = await client.runs.wait(
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
            }
        )

        print(f"\n✓ Run completed successfully!")
        print(f"\nResult keys: {list(result.keys())}")

        if "final_response" in result:
            print(f"\n📊 Final Response:\n{result['final_response']}")
        elif "values" in result:
            print(f"\n📊 Values:\n{result['values']}")
        else:
            print(f"\n📊 Full result:\n{result}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_router_simple())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
