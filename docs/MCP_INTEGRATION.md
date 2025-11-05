# MCP Integration

The Router Agent is exposed as both an A2A (Agent-to-Agent) agent and an MCP (Model Context Protocol) server simultaneously via LangGraph Server's built-in support.

## Overview

LangGraph Server (>= 0.2.3) automatically exposes all deployed agents as MCP tools at the `/mcp` endpoint. This means the Router Agent is accessible via:

1. **A2A Protocol**: `http://localhost:2024/a2a/router` (JSON-RPC)
2. **MCP Protocol**: `http://localhost:2024/mcp` (tool name: `router`)

No additional server process or configuration is required - both protocols work simultaneously from the same LangGraph Server instance.

## Requirements

- `langgraph-api >= 0.2.3` ✅ (current: 0.5.4)
- `langgraph-sdk >= 0.1.61` ✅ (current: 0.2.9)

## How It Works

### Automatic Tool Exposure

When LangGraph Server starts, it:
1. Reads `langgraph.json` graph definitions
2. Inspects each graph's input schema (RouterState)
3. Automatically creates MCP tool definitions
4. Exposes them at the `/mcp` endpoint

### Tool Attributes

For the router agent:
- **Name**: `"router"` (from graph ID)
- **Description**: From `langgraph.json` (see Configuration section)
- **Input Schema**: Derived from `RouterState` TypedDict

## Configuration

The `langgraph.json` file now includes descriptions that become MCP tool documentation:

```json
{
  "graphs": {
    "router": {
      "path": "src.agents.router_agent:create_router_graph",
      "description": "Intelligent orchestrator for ITEP platform..."
    }
  }
}
```

The description appears in MCP tool listings and helps LLMs understand when to use the tool.

## Usage Examples

### From Python (via httpx)

```python
import httpx
import asyncio

async def call_router_via_mcp():
    url = "http://localhost:2024/mcp/call_tool"

    payload = {
        "name": "router",
        "arguments": {
            "messages": [
                {
                    "role": "user",
                    "content": "Fix SonarQube violations in my code"
                }
            ],
            "config": {
                "configurable": {
                    "mode": "auto"
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=120.0)
        result = response.json()
        print(result["final_response"])

asyncio.run(call_router_via_mcp())
```

### From MCP Clients (Claude Desktop, etc.)

MCP clients can discover the router tool via `/mcp/list_tools` and invoke it:

```json
{
  "name": "router",
  "description": "Intelligent orchestrator for ITEP platform...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "messages": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "role": {"type": "string"},
            "content": {"type": "string"}
          }
        }
      },
      "config": {
        "type": "object",
        "properties": {
          "configurable": {
            "type": "object",
            "properties": {
              "mode": {"enum": ["auto", "interactive", "review"]}
            }
          }
        }
      }
    }
  }
}
```

### Claude Desktop Configuration

To use the Router Agent from Claude Desktop, add to your MCP settings:

```json
{
  "mcpServers": {
    "router-agent": {
      "url": "http://localhost:2024/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Then Claude can call the router tool directly:
```
User: "Use the router tool to fix SonarQube violations"
Claude: [Calls router tool with request]
```

## Testing

Run the test suite to verify MCP endpoint functionality:

```bash
# Start LangGraph server
uv run langgraph dev --no-browser

# In another terminal, test MCP endpoint
python test_mcp_endpoint.py
```

The test verifies:
1. ✅ MCP tools list endpoint (`/mcp/list_tools`)
2. ✅ Router tool schema is correct
3. ✅ Router tool can be called and returns results

## Design Considerations

### Stateless Requests

**Important**: MCP requests are stateless and independent. Each tool call is a separate invocation with no session continuity.

**Implication**: Interactive mode (approval workflow) will NOT work via MCP. The Router automatically uses "auto" mode for MCP calls.

### Input Schema Complexity

The Router's `RouterState` exposes many internal fields:
- `messages` (required)
- `config` (for mode selection)
- Many optional internal fields (plan, task_results, etc.)

**For MCP clients**: Only provide `messages` and optionally `config`. Other fields are initialized automatically.

**Example minimal call**:
```json
{
  "name": "router",
  "arguments": {
    "messages": [
      {"role": "user", "content": "Your request here"}
    ]
  }
}
```

### Timeouts

Complex requests can take 30-120 seconds. MCP clients should:
- Set appropriate timeouts (recommended: 120s)
- Handle timeout errors gracefully
- Consider showing "processing..." status to users

### Error Handling

The Router returns error information in the response:
- Validation failures: `is_valid: false`, `rejection_reason` set
- Execution failures: Check `task_results` for failed tasks
- System errors: HTTP error codes (500, etc.)

## Protocol Comparison

### A2A Protocol
- **Use case**: Agent-to-agent communication
- **Format**: JSON-RPC 2.0
- **Endpoint**: `/a2a/router`
- **Features**: Full protocol support, streaming, sessions
- **Best for**: Other agents calling the router

### MCP Protocol
- **Use case**: LLM tool access
- **Format**: MCP Streamable HTTP
- **Endpoint**: `/mcp` (tool name: `router`)
- **Features**: Simple tool interface, stateless
- **Best for**: Claude Desktop, IDEs, human-in-loop tools

## Advantages of Dual Protocol Support

1. **Single Deployment**: One Router instance serves both protocols
2. **No Additional Servers**: No separate MCP server process needed
3. **Consistency**: Same logic, same agents, same behavior
4. **Flexibility**: Choose protocol based on client needs
5. **Cost Effective**: One server to maintain, monitor, and scale

## Limitations

### No Session Support
MCP requests are stateless. Cannot maintain conversation history across tool calls.

**Workaround**: Include relevant context in each message.

### No Interactive Mode
Human-in-the-loop approval doesn't work in MCP (no way to pause and resume).

**Workaround**: Force `mode: "auto"` for MCP clients.

### No Streaming
MCP tools return final results only, no intermediate progress updates.

**Workaround**: For streaming, use A2A protocol or LangGraph SDK directly.

## Troubleshooting

### MCP endpoint returns 404
- Verify LangGraph Server version: `uv pip list | grep langgraph-api`
- Must be >= 0.2.3
- Restart server after upgrading

### Router tool not in list_tools response
- Check `langgraph.json` syntax is valid
- Verify router graph is registered: check server startup logs
- Look for "Registering graph with id 'router'"

### Tool call returns error
- Check LangGraph server logs for details
- Verify ANTHROPIC_API_KEY is set
- Test router with A2A first to isolate MCP issues

### Claude Desktop can't find tools
- Verify MCP server URL is correct
- Check transport is set to "streamable-http"
- Restart Claude Desktop after config changes
- Check Claude Desktop logs for connection errors

## Best Practices

1. **Always set timeout**: Router can take 30-120s for complex requests
2. **Use auto mode**: Don't try interactive mode via MCP
3. **Include context**: Since stateless, include all needed context in each message
4. **Handle errors**: Check for validation failures and task errors
5. **Monitor performance**: Track request duration, success rate

## Further Reading

- [LangGraph MCP Documentation](https://docs.langchain.com/langsmith/server-mcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [A2A Protocol Documentation](architecture.md#a2a-protocol-implementation)

## Summary

✅ **Router Agent is now accessible via both A2A and MCP protocols**

- A2A: Full-featured agent communication for agent-to-agent scenarios
- MCP: Simple tool interface for LLM clients like Claude Desktop

Both protocols work simultaneously from a single LangGraph Server instance, requiring no additional infrastructure or configuration beyond what's already in place.
