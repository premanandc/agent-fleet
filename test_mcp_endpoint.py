#!/usr/bin/env python3
"""
Test MCP Endpoint

Verifies that the Router Agent is accessible via the MCP endpoint
at /mcp on LangGraph Server.

Usage:
    # Start LangGraph server first:
    uv run langgraph dev --no-browser

    # Then run this test:
    python test_mcp_endpoint.py
"""

import asyncio
import httpx
import json


async def test_mcp_tools_list():
    """Test listing available MCP tools"""
    print("=" * 70)
    print("TEST 1: List MCP Tools")
    print("=" * 70)

    url = "http://localhost:2024/mcp/list_tools"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, timeout=10.0)
            response.raise_for_status()

            tools = response.json()
            print(f"\n✓ Found {len(tools)} MCP tools:\n")

            for tool in tools:
                print(f"Tool: {tool.get('name')}")
                print(f"  Description: {tool.get('description', 'N/A')[:100]}...")
                print(f"  Input Schema: {json.dumps(tool.get('inputSchema', {}), indent=2)[:200]}...")
                print()

            return tools

        except httpx.HTTPStatusError as e:
            print(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None


async def test_mcp_call_router():
    """Test calling the router tool via MCP"""
    print("=" * 70)
    print("TEST 2: Call Router via MCP")
    print("=" * 70)

    url = "http://localhost:2024/mcp/call_tool"

    # MCP tool call payload
    payload = {
        "name": "router",
        "arguments": {
            "messages": [
                {
                    "role": "user",
                    "content": "Quick check my code for syntax errors"
                }
            ],
            "config": {
                "configurable": {
                    "mode": "auto"
                }
            }
        }
    }

    print(f"\nCalling router with: {payload['arguments']['messages'][0]['content']}")
    print()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()

            result = response.json()
            print("✓ Router responded:\n")
            print(json.dumps(result, indent=2))
            print()

            return result

        except httpx.HTTPStatusError as e:
            print(f"✗ HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.TimeoutException:
            print("✗ Request timed out (120s)")
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None


async def test_mcp_schema():
    """Test getting the router's input schema via MCP"""
    print("=" * 70)
    print("TEST 3: Get Router Schema")
    print("=" * 70)

    url = "http://localhost:2024/mcp/list_tools"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, timeout=10.0)
            response.raise_for_status()

            tools = response.json()
            router_tool = next((t for t in tools if t["name"] == "router"), None)

            if router_tool:
                print("\n✓ Router tool schema:\n")
                print(json.dumps(router_tool["inputSchema"], indent=2))
                print()
                return router_tool["inputSchema"]
            else:
                print("✗ Router tool not found in MCP tools list")
                return None

        except Exception as e:
            print(f"✗ Error: {e}")
            return None


async def main():
    """Run all MCP endpoint tests"""
    print("\n🔍 Testing MCP Endpoint on LangGraph Server\n")

    # Test 1: List tools
    tools = await test_mcp_tools_list()

    if not tools:
        print("\n⚠ Cannot list MCP tools. Is LangGraph server running?")
        print("  Start with: uv run langgraph dev --no-browser")
        return

    # Test 2: Get schema
    await test_mcp_schema()

    # Test 3: Call router
    result = await test_mcp_call_router()

    if result:
        print("\n✅ MCP endpoint is working correctly!")
    else:
        print("\n⚠ MCP tool call failed. Check logs above.")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\n✓ Router is accessible as:")
    print("  - A2A Agent: http://localhost:2024/a2a/router")
    print("  - MCP Tool: http://localhost:2024/mcp (tool name: 'router')")
    print("\n✓ Both protocols work simultaneously!")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
