#!/usr/bin/env python3
"""
Quick Test Client for Router Agent

This script demonstrates how to invoke the Router agent via LangGraph Server.
"""

import requests
import json
import time
from typing import Optional


class RouterClient:
    """Simple client for interacting with Router Agent via LangGraph Server"""

    def __init__(self, base_url: str = "http://localhost:2024"):
        self.base_url = base_url
        self.router_assistant_id = None

    def discover_router(self) -> Optional[str]:
        """Find the Router agent's assistant ID"""
        print("🔍 Discovering Router agent...")

        # In the newer API, we can use the graph_id directly as assistant_id
        # Try common graph IDs
        for graph_id in ["router", "Router", "router-agent"]:
            try:
                # Test if this assistant exists by trying to get its info
                response = requests.get(f"{self.base_url}/assistants/{graph_id}")
                if response.status_code == 200:
                    self.router_assistant_id = graph_id
                    print(f"✓ Found Router: {self.router_assistant_id}")
                    return self.router_assistant_id
            except:
                continue

        # Fallback: just use "router" as the ID
        self.router_assistant_id = "router"
        print(f"✓ Using default Router ID: {self.router_assistant_id}")
        return self.router_assistant_id

    def list_all_agents(self):
        """List all available agents"""
        print("\n📋 Available Agents:")
        print("-" * 70)

        # Known agents from langgraph.json
        known_agents = ["router", "quick_agent", "slow_agent", "task_breakdown"]

        for agent_id in known_agents:
            try:
                response = requests.get(f"{self.base_url}/assistants/{agent_id}")
                if response.status_code == 200:
                    print(f"  ✓ {agent_id:20s}")
                else:
                    print(f"  ✗ {agent_id:20s} (not available)")
            except:
                print(f"  ✗ {agent_id:20s} (error)")

        print("-" * 70)

    def invoke_router(self, message: str, mode: str = "auto", stream: bool = False):
        """Invoke the Router agent with a user message"""

        if not self.router_assistant_id:
            self.discover_router()

        if not self.router_assistant_id:
            print("❌ Cannot invoke Router - agent not found")
            return

        print(f"\n💬 User Request: {message}")
        print(f"⚙️  Mode: {mode}")
        print("-" * 70)

        # Create a new thread and run
        payload = {
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            },
            "assistant_id": self.router_assistant_id,
            "config": {
                "configurable": {
                    "mode": mode
                }
            },
            "stream_mode": ["values"]
        }

        if stream:
            return self._invoke_streaming(payload)
        else:
            return self._invoke_sync(payload)

    def _invoke_sync(self, payload: dict):
        """Synchronous invocation"""
        print("⏳ Invoking Router (synchronous)...")

        start_time = time.time()

        # Use /runs/stream endpoint with stream_mode="values" to get final state
        response = requests.post(
            f"{self.base_url}/runs/stream",
            json=payload,
            timeout=120
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            # Collect all streamed events and get the last one
            last_state = None
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            event = json.loads(line_str[6:])
                            if event.get('data'):
                                last_state = event['data']
                        except json.JSONDecodeError:
                            continue

            if last_state:
                self._display_result(last_state, elapsed)
                return last_state
            else:
                print("❌ No result received")
                return None
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None

    def _invoke_streaming(self, payload: dict):
        """Streaming invocation"""
        print("⏳ Invoking Router (streaming)...")
        print()

        start_time = time.time()

        response = requests.post(
            f"{self.base_url}/runs/stream",
            json=payload,
            stream=True,
            timeout=120
        )

        response.raise_for_status()

        # Process streaming events
        last_state = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        event = json.loads(data_str)
                        last_state = event
                        self._display_stream_event(event)
                    except json.JSONDecodeError:
                        continue

        elapsed = time.time() - start_time

        if last_state:
            print()
            print("=" * 70)
            self._display_result(last_state, elapsed)
            return last_state

    def _display_stream_event(self, event: dict):
        """Display streaming event"""
        # Simple display - just show we're making progress
        if "messages" in event:
            print(".", end="", flush=True)

    def _display_result(self, result: dict, elapsed: float):
        """Display final result"""
        print()
        print("=" * 70)
        print("📊 RESULT")
        print("=" * 70)

        # Extract final response
        final_response = result.get("final_response")
        if final_response:
            print(f"\n{final_response}")
        else:
            # Try to get last AI message
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    print(f"\n{last_msg.content}")
                elif isinstance(last_msg, dict):
                    print(f"\n{last_msg.get('content', 'No content')}")

        # Show metadata
        print()
        print("-" * 70)
        print(f"⏱️  Execution time: {elapsed:.2f}s")

        if "task_results" in result:
            print(f"✅ Tasks completed: {len(result['task_results'])}")

            for idx, task in enumerate(result["task_results"], 1):
                status_icon = "✓" if task.get("status") == "completed" else "✗"
                print(f"   {status_icon} Task {idx}: {task.get('description', 'N/A')[:50]}... ({task.get('agent_name', 'unknown')})")

        print("=" * 70)


def main():
    """Run interactive test client"""
    print("=" * 70)
    print("Router Agent Test Client")
    print("=" * 70)

    client = RouterClient()

    # List all available agents
    client.list_all_agents()

    # Discover Router
    if not client.discover_router():
        print("\n❌ Router agent not found. Is the server running?")
        print("   Start server with: uv run langgraph dev --no-browser")
        return

    print("\n" + "=" * 70)
    print("Test Scenarios")
    print("=" * 70)

    # Test 1: Quick validation
    print("\n🧪 TEST 1: Quick Validation (should use QuickAgent)")
    client.invoke_router(
        message="Can you quickly validate the syntax of my code?",
        mode="auto",
        stream=False
    )

    time.sleep(2)

    # Test 2: Deep fixing
    print("\n\n🧪 TEST 2: Deep Fix (should use SlowAgent)")
    client.invoke_router(
        message="Fix all the SonarQube violations in my codebase",
        mode="auto",
        stream=False
    )

    time.sleep(2)

    # Test 3: Parallel execution
    print("\n\n🧪 TEST 3: Parallel Execution (should use both agents)")
    client.invoke_router(
        message="Quick check my code and then fix any SonarQube issues",
        mode="auto",
        stream=True
    )

    print("\n\n" + "=" * 70)
    print("✅ All tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except requests.exceptions.ConnectionError:
        print("\n\n❌ Cannot connect to LangGraph Server")
        print("   Make sure the server is running:")
        print("   uv run langgraph dev --no-browser")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
