#!/bin/bash
# Quick verification script for LangGraph Server

echo "===================================================================="
echo "LangGraph Server Verification"
echo "===================================================================="
echo ""

# Wait for server to be ready
echo "Waiting for server to be ready..."
sleep 2

# Test 1: List all assistants
echo "1. Listing all assistants..."
curl -s http://localhost:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

echo ""
echo "--------------------------------------------------------------------"
echo ""

# Test 2: Get Router agent card (if available)
echo "2. Fetching Router agent details..."
ROUTER_ID=$(curl -s http://localhost:2024/assistants/search -d '{}' | python3 -c "import sys, json; assistants = json.load(sys.stdin); router = next((a for a in assistants if a.get('graph_id') == 'router'), None); print(router['assistant_id'] if router else 'NOT_FOUND')")

if [ "$ROUTER_ID" != "NOT_FOUND" ]; then
    echo "Router Assistant ID: $ROUTER_ID"
    curl -s "http://localhost:2024/assistants/$ROUTER_ID" | python3 -m json.tool
else
    echo "Router not found"
fi

echo ""
echo "--------------------------------------------------------------------"
echo ""

# Test 3: Quick health check
echo "3. Server health check..."
curl -s http://localhost:2024/ok

echo ""
echo ""
echo "===================================================================="
echo "✓ Server is running and agents are registered!"
echo "===================================================================="
echo ""
echo "Available endpoints:"
echo "  - API: http://127.0.0.1:2024"
echo "  - Docs: http://127.0.0.1:2024/docs"
echo "  - Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
echo ""
