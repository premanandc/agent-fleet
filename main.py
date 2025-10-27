"""Main entry point for the task breakdown agent."""

import os
from dotenv import load_dotenv

from src.agents.task_breakdown import TaskBreakdownAgent


def main():
    """Run example task breakdown scenarios."""
    # Load environment variables from .env file
    load_dotenv()

    # Example 1: Simple task (should not need breakdown)
    print("=" * 60)
    print("Example 1: Simple Task")
    print("=" * 60)

    agent = TaskBreakdownAgent(provider="anthropic")
    result = agent.run("Write a function to calculate factorial")

    display(result)

    # Example 2: Complex task (should need breakdown)
    print("\n" + "=" * 60)
    print("Example 2: Complex Task")
    print("=" * 60)

    result = agent.run(
        "Build a full-stack web application with user authentication, "
        "database integration, and REST API"
    )

    display(result)

    # Example 3: Using OpenAI (if configured)
    if os.getenv("OPENAI_API_KEY"):
        print("\n" + "=" * 60)
        print("Example 3: Using OpenAI")
        print("=" * 60)

        agent_openai = TaskBreakdownAgent(provider="openai")
        result = agent_openai.run(
            "Implement a machine learning pipeline for image classification"
        )

        display(result)

def display(result: dict):
    print(f"\nTask: {result['task']}")
    print(f"\nNeeds Breakdown: {result['needs_breakdown']}")
    print(f"\nAnalysis:\n{result['analysis']}")
    if result['steps']:
        print(f"\nSteps:")
        for i, step in enumerate(result['steps'], 1):
            print(f"  {i}. {step}")


if __name__ == "__main__":
    main()
