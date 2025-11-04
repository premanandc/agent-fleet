"""
Simple test to verify A2A SDK integration in execute.py

This test verifies that:
1. The a2a-sdk is properly installed
2. Imports work correctly
3. The refactored code structure is valid
"""

import asyncio
import sys


async def test_imports():
    """Test that all A2A SDK imports work"""
    print("Testing A2A SDK imports...")

    try:
        from a2a.client import A2AClient, A2ACardResolver, create_text_message_object, A2AClientHTTPError, A2AClientJSONError
        print("✓ A2AClient and A2ACardResolver imported successfully")
        print("✓ create_text_message_object imported successfully")
        print("✓ A2A exceptions imported successfully")

        from a2a.types import SendMessageRequest, MessageSendParams
        print("✓ SendMessageRequest and MessageSendParams imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("\nPlease install a2a-sdk:")
        print("  uv sync")
        return False


async def test_execute_imports():
    """Test that execute.py imports work"""
    print("\nTesting execute.py imports...")

    try:
        from src.nodes.execute import execute_tasks, _invoke_agent
        print("✓ execute.py imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


async def test_message_construction():
    """Test that we can construct A2A messages"""
    print("\nTesting A2A message construction...")

    try:
        from a2a.types import SendMessageRequest, MessageSendParams
        from a2a.client import create_text_message_object
        from uuid import uuid4

        # Test using helper function
        message = create_text_message_object(
            content='Test message'
        )

        print(f"✓ Message created with helper: {message.message_id}")

        # Test message payload construction
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Test message'}
                ],
                'messageId': f"msg_{uuid4().hex}",
            },
            'thread': {
                'threadId': 'test_thread'
            }
        }

        # Create request
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )

        print(f"✓ SendMessageRequest constructed successfully")
        print(f"  Request ID: {request.id}")

        return True
    except Exception as e:
        print(f"✗ Message construction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 70)
    print("A2A SDK Integration Test")
    print("=" * 70)
    print()

    results = []

    # Test imports
    results.append(await test_imports())

    # Only continue if imports work
    if results[0]:
        results.append(await test_execute_imports())
        results.append(await test_message_construction())

    print()
    print("=" * 70)

    if all(results):
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("  1. Install a2a-sdk if not already: pip install a2a-sdk")
        print("  2. Restart the LangGraph server")
        print("  3. Run the router agent with a test request")
        return 0
    else:
        print("❌ Some tests failed")
        print()
        print("Please fix the issues above before proceeding")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
