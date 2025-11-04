# A2A Protocol Implementation

This document explains how the Router Agent uses the A2A (Agent-to-Agent) protocol to communicate with subordinate agents.

## Overview

A2A is Google's protocol for enabling communication between conversational AI agents. LangGraph Server implements A2A support at the `/a2a/{assistant_id}` endpoint.

**Key Point:** A2A uses **JSON-RPC 2.0** format, not REST-style requests.

## Request Format

### Correct A2A Request (JSON-RPC 2.0)

```python
a2a_request = {
    "jsonrpc": "2.0",
    "id": task['id'],
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Your message here"
                }
            ]
        },
        "messageId": f"msg_{task['id']}",
        "thread": {
            "threadId": f"router_task_{task['id']}"
        }
    }
}
```

### ❌ Incorrect Format (What We Had Before)

```python
# This causes 400 Bad Request
a2a_request = {
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "Your message here"
            }
        ]
    },
    "config": {
        "configurable": {
            "thread_id": f"router_task_{task['id']}"
        }
    },
    "stream_mode": "values"
}
```

## Response Format

The A2A endpoint returns a JSON-RPC 2.0 response:

### Success Response

```json
{
  "jsonrpc": "2.0",
  "id": "task_abc123",
  "result": {
    "message": {
      "role": "assistant",
      "parts": [
        {
          "kind": "text",
          "text": "Agent's response here"
        }
      ]
    }
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": "task_abc123",
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

## Implementation in execute.py

### Request Construction

```python
# Build A2A request (JSON-RPC 2.0 format)
a2a_request = {
    "jsonrpc": "2.0",
    "id": task['id'],
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": agent_message
                }
            ]
        },
        "messageId": f"msg_{task['id']}",
        "thread": {
            "threadId": f"router_task_{task['id']}"
        }
    }
}

# Send request
response = await client.post(
    f"{langgraph_url}/a2a/{agent_id}",
    json=a2a_request,
    timeout=300.0
)
```

### Response Parsing

```python
response.raise_for_status()
response_data = response.json()

# Check for JSON-RPC error
if "error" in response_data:
    error_info = response_data["error"]
    error_msg = error_info.get("message", str(error_info))
    raise Exception(f"A2A agent returned error: {error_msg}")

# Extract result
result = response_data.get("result", {})
message = result.get("message", {})
parts = message.get("parts", [])

# Extract text from parts
text_parts = []
for part in parts:
    if isinstance(part, dict) and part.get("kind") == "text":
        text_parts.append(part.get("text", ""))

agent_result = "\n".join(text_parts)
```

## JSON-RPC 2.0 Specification

The A2A protocol follows [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification):

### Required Fields in Request

- `jsonrpc`: Must be exactly "2.0"
- `id`: Unique identifier for the request
- `method`: The method to invoke (for A2A: "message/send")
- `params`: Method parameters

### Response Fields

- `jsonrpc`: "2.0"
- `id`: Matches the request ID
- `result`: The successful result (if no error)
- `error`: Error object (if failed)

## Message Parts

The A2A protocol uses a `parts` array for message content, allowing for different content types:

### Text Part

```json
{
  "kind": "text",
  "text": "Your message content"
}
```

### Future: Other Part Types

While currently we only use text, the A2A protocol can support:
- Images
- Files
- Structured data
- Tool calls

## Thread Management

The `thread.threadId` parameter enables conversation continuity:

```python
"thread": {
    "threadId": f"router_task_{task['id']}"
}
```

This allows subordinate agents to:
- Maintain context across multiple messages
- Access previous interactions
- Build upon prior results

## Error Handling

### HTTP Errors

```python
try:
    response = await client.post(...)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error invoking agent: {e}")
```

### JSON-RPC Errors

```python
if "error" in response_data:
    error_code = response_data["error"].get("code")
    error_msg = response_data["error"].get("message")
    logger.error(f"A2A error {error_code}: {error_msg}")
```

### Common Error Codes

- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid Request (malformed JSON-RPC)
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

## Testing A2A Requests

### Manual Test with curl

```bash
curl -X POST http://localhost:2024/a2a/{assistant_id} \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test123",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "Hello agent"
          }
        ]
      },
      "messageId": "msg_test123",
      "thread": {
        "threadId": "test_thread"
      }
    }
  }'
```

### Python Test

```python
import httpx
import asyncio

async def test_a2a():
    client = httpx.AsyncClient()

    request = {
        "jsonrpc": "2.0",
        "id": "test123",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Test message"
                    }
                ]
            },
            "messageId": "msg_test123",
            "thread": {
                "threadId": "test_thread"
            }
        }
    }

    response = await client.post(
        "http://localhost:2024/a2a/YOUR_AGENT_ID",
        json=request
    )

    print(response.json())

asyncio.run(test_a2a())
```

## Debugging Tips

### 1. Check Request Format

```python
import json
logger.info(f"A2A Request: {json.dumps(a2a_request, indent=2)}")
```

### 2. Inspect Response

```python
logger.info(f"A2A Response: {json.dumps(response_data, indent=2)}")
```

### 3. Validate JSON-RPC

Ensure:
- ✅ `jsonrpc` field is "2.0"
- ✅ `id` is included
- ✅ `method` is "message/send"
- ✅ `params.message.parts` is an array
- ✅ Each part has `kind` and appropriate content field

### 4. Check Agent Compatibility

The subordinate agent must:
- Have a `messages` key in its state
- Support A2A protocol
- Have an agent card at `/.well-known/agent-card.json`

## References

- [LangGraph A2A Documentation](https://docs.langchain.com/langsmith/server-a2a)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [A2A Protocol by Google](https://github.com/google/agent-to-agent)

## Summary

**Key Takeaways:**
- ✅ A2A uses JSON-RPC 2.0, not REST format
- ✅ Request must have: `jsonrpc`, `id`, `method`, `params`
- ✅ Message content goes in `params.message.parts` array
- ✅ Each part has `kind` ("text") and content field
- ✅ Response has `result` (success) or `error` (failure)
- ✅ Extract text from `result.message.parts[].text`

**Before (Broken):** REST-style request → 400 Bad Request
**After (Fixed):** JSON-RPC 2.0 format → Successful agent communication
