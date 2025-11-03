#!/usr/bin/env python3
"""
Interactive Chat Client for Router Agent

Usage:
    python chat_with_router.py
    python chat_with_router.py --stream  # Enable streaming
"""

import requests
import json
import argparse
from typing import Optional


def discover_router(base_url: str = "http://localhost:2024") -> Optional[str]:
    """Find the Router agent's assistant ID"""
    response = requests.post(f"{base_url}/assistants/search", json={})
    response.raise_for_status()

    for assistant in response.json():
        if assistant.get("graph_id") == "router":
            return assistant["assistant_id"]

    return None


def invoke_router(assistant_id: str, message: str, mode: str = "auto", stream: bool = False, base_url: str = "http://localhost:2024"):
    """Invoke the Router agent"""

    payload = {
        "input": {
            "messages": [{"role": "user", "content": message}]
        },
        "config": {
            "configurable": {"mode": mode}
        },
        "stream_mode": "values"
    }

    if stream:
        print("\n🤖 Router: ", end="", flush=True)
        response = requests.post(
            f"{base_url}/threads/{assistant_id}/runs/stream",
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        last_state = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        event = json.loads(line_str[6:])
                        last_state = event
                        print(".", end="", flush=True)
                    except:
                        pass

        print()  # New line after dots

        if last_state and "final_response" in last_state:
            print(last_state["final_response"])
        return last_state

    else:
        response = requests.post(
            f"{base_url}/threads/{assistant_id}/runs",
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        result = response.json()
        if "final_response" in result:
            print(f"\n🤖 Router:\n{result['final_response']}")
        return result


def main():
    parser = argparse.ArgumentParser(description="Chat with Router Agent")
    parser.add_argument("--stream", action="store_true", help="Enable streaming")
    parser.add_argument("--mode", default="auto", choices=["auto", "interactive", "review"], help="Execution mode")
    parser.add_argument("--url", default="http://localhost:2024", help="LangGraph Server URL")
    args = parser.parse_args()

    print("=" * 70)
    print("Interactive Chat with Router Agent")
    print("=" * 70)

    # Discover Router
    print("\n🔍 Discovering Router agent...")
    assistant_id = discover_router(args.url)

    if not assistant_id:
        print("❌ Router agent not found!")
        print("   Make sure LangGraph Server is running:")
        print("   uv run langgraph dev --no-browser")
        return

    print(f"✓ Connected to Router: {assistant_id}")
    print(f"⚙️  Mode: {args.mode}")
    print(f"📡 Streaming: {'enabled' if args.stream else 'disabled'}")

    print("\n" + "=" * 70)
    print("Type your requests below (or 'quit' to exit)")
    print("=" * 70)

    # Example requests
    print("\n💡 Example requests:")
    print("  • Quick check my code")
    print("  • Fix SonarQube violations")
    print("  • Validate my code and fix any issues")
    print()

    # Interactive loop
    while True:
        try:
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break

            # Invoke Router
            invoke_router(
                assistant_id=assistant_id,
                message=user_input,
                mode=args.mode,
                stream=args.stream,
                base_url=args.url
            )

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Error communicating with server: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
