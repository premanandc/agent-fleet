"""Test script for the task breakdown agent via LangGraph API and A2A protocol."""

import requests
import json
import time


def test_agent(task: str, base_url: str = "http://127.0.0.1:2024"):
    """
    Test the task breakdown agent via LangGraph API.

    Args:
        task: The task to send to the agent
        base_url: Base URL of the LangGraph server
    """
    print(f"\n{'='*60}")
    print(f"Testing Task Breakdown Agent")
    print(f"{'='*60}")
    print(f"\nTask: {task}")

    try:
        # Step 1: Create a thread
        thread_response = requests.post(f"{base_url}/threads", json={})
        thread_response.raise_for_status()
        thread = thread_response.json()
        thread_id = thread["thread_id"]
        print(f"\nCreated thread: {thread_id}")

        # Step 2: Run the agent
        run_payload = {
            "assistant_id": "task_breakdown",
            "input": {
                "messages": [{"role": "user", "content": task}]
            }
        }
        run_response = requests.post(
            f"{base_url}/threads/{thread_id}/runs",
            json=run_payload
        )
        run_response.raise_for_status()
        run = run_response.json()
        run_id = run["run_id"]
        print(f"Started run: {run_id}")

        # Step 3: Wait for completion and get state
        print("Waiting for agent to complete...")
        max_attempts = 20
        for attempt in range(max_attempts):
            time.sleep(0.5)

            run_status_response = requests.get(
                f"{base_url}/threads/{thread_id}/runs/{run_id}"
            )
            run_status = run_status_response.json()

            if run_status["status"] == "success":
                print("Agent completed successfully!")
                break
            elif run_status["status"] in ["error", "failed"]:
                print(f"Agent failed with status: {run_status['status']}")
                return None

        # Step 4: Get the final state
        state_response = requests.get(f"{base_url}/threads/{thread_id}/state")
        state_response.raise_for_status()
        state = state_response.json()

        # Extract and display results
        print(f"\n{'='*60}")
        print("Agent Response:")
        print(f"{'='*60}")

        values = state.get("values", {})

        # Display the AI message
        messages = values.get("messages", [])
        for msg in messages:
            if msg.get("type") == "ai":
                print(f"\n{msg['content']}")

        # Display the breakdown details
        if values.get("needs_breakdown"):
            print(f"\n{'='*60}")
            print("Breakdown Details:")
            print(f"{'='*60}")
            steps = values.get("steps", [])
            print(f"\nTotal steps: {len(steps)}")
            for i, step in enumerate(steps, 1):
                print(f"{i}. {step}")
        else:
            print("\nTask was simple enough, no breakdown needed.")

        return state

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


def test_agent_a2a(task: str, base_url: str = "http://127.0.0.1:2024"):
    """
    Test the task breakdown agent via A2A protocol.

    Args:
        task: The task to send to the agent
        base_url: Base URL of the LangGraph server
    """
    print(f"\n{'='*60}")
    print(f"Testing Task Breakdown Agent via A2A Protocol")
    print(f"{'='*60}")
    print(f"\nTask: {task}")

    try:
        # Step 1: Search for assistants to get the assistant_id
        search_response = requests.post(f"{base_url}/assistants/search", json={})
        search_response.raise_for_status()
        assistants = search_response.json()

        # Find our task_breakdown assistant
        assistant = None
        for asst in assistants:
            if asst.get("graph_id") == "task_breakdown":
                assistant = asst
                break

        if not assistant:
            print("Error: task_breakdown assistant not found")
            return None

        assistant_id = assistant["assistant_id"]
        print(f"\nFound assistant: {assistant_id}")

        # Step 2: Send message via A2A protocol
        a2a_payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": task
                        }
                    ]
                }
            },
            "id": 1
        }

        print(f"Sending A2A request...")
        a2a_response = requests.post(
            f"{base_url}/a2a/{assistant_id}",
            json=a2a_payload,
            timeout=30
        )
        a2a_response.raise_for_status()
        result = a2a_response.json()

        # Extract and display results
        print(f"\n{'='*60}")
        print("A2A Response:")
        print(f"{'='*60}")

        if "result" in result:
            a2a_result = result["result"]

            # Display task status
            if "status" in a2a_result:
                status = a2a_result["status"]
                print(f"\nTask Status: {status.get('state')}")

            # Display agent response from history
            if "history" in a2a_result:
                for msg in a2a_result["history"]:
                    if msg.get("role") == "agent":
                        for part in msg.get("parts", []):
                            if part.get("kind") == "text":
                                print(f"\nAgent Message:")
                                print(part["text"])

            # Display artifacts
            if "artifacts" in a2a_result:
                print(f"\n{'='*60}")
                print("Artifacts:")
                print(f"{'='*60}")
                for artifact in a2a_result["artifacts"]:
                    print(f"\nArtifact: {artifact.get('name')}")
                    for part in artifact.get("parts", []):
                        if part.get("kind") == "text":
                            print(part["text"])

        return result

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING VIA LANGGRAPH THREADS API")
    print("="*60)

    # Test 1: Simple task via Threads API
    test_agent("Write a function to calculate factorial")

    # Test 2: Complex task via Threads API
    test_agent(
        "Build a full-stack web application with user authentication, "
        "database integration, and REST API"
    )

    print("\n\n" + "="*60)
    print("TESTING VIA A2A PROTOCOL")
    print("="*60)

    # Test 3: Simple task via A2A
    test_agent_a2a("Write a function to calculate factorial")

    # Test 4: Complex task via A2A
    test_agent_a2a(
        "Implement a machine learning pipeline for image classification "
        "with data preprocessing, model training, and evaluation"
    )
