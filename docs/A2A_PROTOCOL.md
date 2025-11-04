# A2A Protocol Implementation

This document explains how the Router Agent uses the A2A (Agent-to-Agent) protocol to communicate with subordinate agents.

## Overview

A2A is Google's protocol for enabling communication between conversational AI agents. LangGraph Server implements A2A support at the `/a2a/{assistant_id}` endpoint.

**Key Point:** A2A uses **JSON-RPC 2.0** format, not REST-style requests.

**Recommendation:** Use the official **a2a-sdk** package instead of manual JSON-RPC construction for cleaner, more maintainable code.

## Using the A2A SDK (Recommended)

The Router Agent now uses the official **a2a-sdk** package to handle A2A communication. This provides significant advantages over manual JSON-RPC construction.

### Installation

```bash
# Add to pyproject.toml
dependencies = [
    "a2a-sdk>=0.3.10",
]

# Install
uv sync
# or
pip install a2a-sdk
```

### SDK Implementation (Current)

```python
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, AgentCard
import httpx

async def invoke_agent(agent_id: str, message: str, task_id: str):
    """
    Invoke a subordinate agent using the A2A SDK
    """
    async with httpx.AsyncClient() as client:
        # 1. Fetch agent card (LangGraph uses query params)
        # Format: GET /.well-known/agent-card.json?assistant_id={agent_id}
        card_response = await client.get(
            "http://localhost:2024/.well-known/agent-card.json",
            params={"assistant_id": agent_id},
            timeout=10.0
        )
        card_response.raise_for_status()
        agent_card_data = card_response.json()

        # Parse JSON into AgentCard Pydantic model
        agent_card = AgentCard(**agent_card_data)

        # 2. Create A2A client
        a2a_client = A2AClient(
            httpx_client=client,
            agent_card=agent_card,  # Must be AgentCard object, not dict
            url=f"http://localhost:2024/a2a/{agent_id}"
        )

        # 3. Prepare message
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message}],
                'messageId': f"msg_{task_id}",
            },
            'thread': {
                'threadId': f"thread_{task_id}"
            }
        }

        # 4. Create request
        request = SendMessageRequest(
            id=task_id,
            params=MessageSendParams(**send_message_payload)
        )

        # 5. Send message (JSON-RPC handled automatically)
        response = await a2a_client.send_message(
            request,
            http_kwargs={'timeout': 300.0}
        )

        # 6. Extract result from response
        # SendMessageResponse is a RootModel wrapping either error or success
        from a2a.types import SendMessageSuccessResponse, Message

        if isinstance(response.root, SendMessageSuccessResponse):
            success_response = response.root
            result = success_response.result  # Can be Task or Message

            if isinstance(result, Message):
                # Extract text from message parts
                if result.parts:
                    text_parts = [
                        part.text
                        for part in result.parts
                        if hasattr(part, 'kind') and part.kind == 'text'
                    ]
                    return "\n".join(text_parts)

            return str(result)
        else:
            # Error response
            raise Exception(f"A2A error: {response.root.error}")
```

### SDK Advantages

✅ **Automatic JSON-RPC handling** - No need to construct `jsonrpc`, `method`, `params` manually
✅ **Type-safe message building** - Pydantic models prevent errors
✅ **Built-in error handling** - `A2AClientHTTPError`, `A2AClientJSONError`
✅ **Agent card resolution** - Automatic fetching and parsing
✅ **Helper functions** - `create_text_message_object()` for quick messages
✅ **Streaming support** - `send_message_streaming()` for real-time responses

### LangGraph-Specific: Agent Card Fetching

**Important:** LangGraph Server uses query parameters for agent cards, not path-based URLs:

```python
# ✅ Correct for LangGraph
from a2a.types import AgentCard

card_response = await client.get(
    f"{langgraph_url}/.well-known/agent-card.json",
    params={"assistant_id": agent_id},  # Query parameter!
    timeout=10.0
)
card_response.raise_for_status()
agent_card_data = card_response.json()

# IMPORTANT: Parse into AgentCard object
agent_card = AgentCard(**agent_card_data)

# ❌ Wrong - passing dict directly causes AttributeError
a2a_client = A2AClient(
    httpx_client=client,
    agent_card=agent_card_data,  # dict - will fail!
    url=...
)

# ✅ Correct - pass AgentCard object
a2a_client = A2AClient(
    httpx_client=client,
    agent_card=agent_card,  # AgentCard object
    url=...
)
```

**Common Errors:**
- ❌ Using `A2ACardResolver` with path-based URLs → 404 errors
- ❌ Passing raw dict to `A2AClient` → `'dict' object has no attribute 'supports_authenticated_extended_card'`
- ❌ Accessing `response.result` directly → `'SendMessageResponse' object has no attribute 'result'`

**Correct Response Access:**
`SendMessageResponse` is a Pydantic `RootModel` that wraps either a success or error response:
```python
from a2a.types import SendMessageSuccessResponse

if isinstance(response.root, SendMessageSuccessResponse):
    success_response = response.root
    result = success_response.result  # Now you can access .result
else:
    error_response = response.root
    # Handle error
```

The `A2ACardResolver` is designed for standard A2A servers that use path-based card URLs. LangGraph uses a query parameter approach instead, and requires manual parsing of the response into an `AgentCard` Pydantic model.

### Helper Functions

The SDK provides convenience functions:

```python
from a2a.client import create_text_message_object

# Quick message creation
message = create_text_message_object(
    role='user',  # or 'agent'
    content='Your message here'
)
```

### Error Handling with SDK

```python
from a2a.client import A2AClientHTTPError, A2AClientJSONError

try:
    response = await a2a_client.send_message(request)
except A2AClientHTTPError as e:
    # Handle HTTP errors (4xx, 5xx)
    logger.error(f"HTTP error: {e}")
except A2AClientJSONError as e:
    # Handle JSON parsing errors
    logger.error(f"JSON error: {e}")
except httpx.TimeoutException:
    # Handle timeouts
    logger.error("Request timed out")
```

## Manual JSON-RPC Implementation (Legacy)

If you need to understand the underlying protocol or can't use the SDK, here's how to construct requests manually.

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

- [A2A Python SDK Documentation](https://a2a-protocol.org/latest/sdk/python/api/a2a.client.html)
- [A2A SDK PyPI Package](https://pypi.org/project/a2a-sdk/)
- [LangGraph A2A Documentation](https://docs.langchain.com/langsmith/server-a2a)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [A2A Protocol by Google](https://github.com/google/agent-to-agent)

## Summary

**Key Takeaways:**
- ✅ **Use the a2a-sdk** for cleaner, more maintainable code
- ✅ SDK handles JSON-RPC 2.0 protocol automatically
- ✅ Type-safe message construction with Pydantic models
- ✅ Built-in error handling (`A2AClientHTTPError`, `A2AClientJSONError`)
- ✅ Automatic agent card resolution
- ✅ Helper functions like `create_text_message_object()`

**Evolution:**
1. ❌ **Initial (Broken):** REST-style request → 400 Bad Request
2. ✅ **Fixed:** Manual JSON-RPC 2.0 → Works but verbose
3. ✅✅ **Current (SDK):** a2a-sdk → Clean, type-safe, maintainable

**Installation:**
```bash
uv sync  # Dependencies already in pyproject.toml
```

**Quick Example:**
```python
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams

# Create client and send message
response = await a2a_client.send_message(request)
```
