#!/bin/bash

# Script to send an evaluation query to the green agent's message/send endpoint via A2A
# Usage: ./evaluate_purple_agent.sh [query_type] [query_index]
#   query_type: Optional. Question type filter (default: "all")
#   query_index: Optional. If provided (0-based index), runs only that specific query. If omitted, runs all queries.
# Example: ./evaluate_purple_agent.sh all
# Example: ./evaluate_purple_agent.sh all 0  # Run only first query
# Example: ./evaluate_purple_agent.sh earnings 5  # Run 6th query of earnings type

set -e

# Hardcoded agent URLs
GREEN_AGENT="http://localhost:9009"
PURPLE_AGENT="http://localhost:9019"

# Parameters
QUERY_TYPE="${1:-all}"
QUERY_INDEX="${2:-}"  # Empty means run all queries

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Green Agent: $GREEN_AGENT"
echo "Purple Agent: $PURPLE_AGENT"
echo "Query Type: $QUERY_TYPE"
if [ -n "$QUERY_INDEX" ]; then
    echo "Query Index: $QUERY_INDEX (running single query)"
else
    echo "Query Index: all (running all queries)"
fi
echo ""

cd "$PROJECT_DIR" && uv run python << PYTHON
import asyncio
import httpx
import json
from uuid import uuid4

async def send_evaluation_request():
    green_agent_url = "$GREEN_AGENT"
    purple_agent_url = "$PURPLE_AGENT"
    query_type = "$QUERY_TYPE"
    query_index_str = "$QUERY_INDEX"

    # Create the evaluation request in the format expected by the green agent
    config = {
        'type': query_type
    }
    
    # Add query_index to config if provided
    if query_index_str and query_index_str.strip():
        try:
            config['query_index'] = int(query_index_str)
        except ValueError:
            print(f"Warning: Invalid query_index '{query_index_str}', ignoring. Using all queries.")
    
    eval_request = {
        'participants': {
            'purple_agent': purple_agent_url
        },
        'config': config
    }
    
    request_text = json.dumps(eval_request)

    async with httpx.AsyncClient(timeout=600.0) as client:
        from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
        from a2a.types import Message, Part, Role, TextPart

        # Get green agent card
        print(f"Retrieving green agent card from {green_agent_url}...")
        resolver = A2ACardResolver(httpx_client=client, base_url=green_agent_url)
        agent_card = await resolver.get_agent_card()
        
        if not agent_card:
            print(f"Error: Could not retrieve agent card from {green_agent_url}")
            return
        
        print(f"Green Agent: {agent_card.name}")
        print(f"Description: {agent_card.description}")
        print("")
        
        # Create A2A client for green agent with streaming enabled
        config = ClientConfig(httpx_client=client, streaming=True)
        factory = ClientFactory(config)
        a2a_client = factory.create(agent_card)
        
        # Create message with evaluation request
        message = Message(
            kind='message',
            role=Role.user,
            parts=[Part(root=TextPart(text=request_text))],
            message_id=uuid4().hex,
            context_id=None
        )
        
        # Send message to green agent
        print(f"Sending evaluation request to green agent...")
        print(f"Request: {json.dumps(eval_request, indent=2)}")
        print("")
        
        events = []
        async for event in a2a_client.send_message(message):
            events.append(event)
            
            if isinstance(event, tuple):
                task, update = event
                print(f'Task ID: {task.id}')
                print(f'Task State: {task.status.state.value}')
                
                if task.status.message:
                    msg_parts = task.status.message.parts if task.status.message.parts else []
                    for part in msg_parts:
                        if hasattr(part, 'root') and hasattr(part.root, 'text'):
                            print(f'Status: {part.root.text}')
                        elif hasattr(part, 'root') and hasattr(part.root, 'data'):
                            print(f'Status: {json.dumps(part.root.data, indent=2)}')
                
                if task.artifacts:
                    print(f'Artifacts: {len(task.artifacts)}')
                    for artifact in task.artifacts:
                        print(f'  - {artifact.name if hasattr(artifact, "name") else "unnamed"}')
                        for part in artifact.parts:
                            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                print(f'    {part.root.text[:200]}...' if len(part.root.text) > 200 else f'    {part.root.text}')
                            elif hasattr(part, 'root') and hasattr(part.root, 'data'):
                                print(f'    {json.dumps(part.root.data, indent=4)}')
            elif isinstance(event, Message):
                print("=== Green Agent Response ===")
                for part in event.parts:
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        print(part.root.text)
                    elif hasattr(part, 'root') and hasattr(part.root, 'data'):
                        print(json.dumps(part.root.data, indent=2))
        
        print("")
        print(f"Evaluation completed! (Events: {len(events)})")

asyncio.run(send_evaluation_request())
PYTHON
