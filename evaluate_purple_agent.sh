#!/bin/bash
# Script to evaluate purple agent via green agent using A2A protocol
# Usage: ./evaluate_purple_agent.sh [query_type]

GREEN_AGENT="http://localhost:9009"
PURPLE_AGENT="http://localhost:9019"
QUERY_TYPE="${1:-Market Analysis}"  # Default to "Market Analysis" if not provided

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/rlingech/Projects/AIML/AgenticAI/RDI/finance-green-agent"

echo "=========================================="
echo "Evaluating Purple Agent via Green Agent"
echo "=========================================="
echo "Green Agent: $GREEN_AGENT"
echo "Purple Agent: $PURPLE_AGENT"
echo "Query Type: $QUERY_TYPE"
echo ""
echo "Sending request..."
echo ""

cd "$PROJECT_DIR" && uv run python << PYTHON
import asyncio
import httpx
import json
from uuid import uuid4

async def evaluate():
    green_agent_url = "$GREEN_AGENT"
    purple_agent_url = "$PURPLE_AGENT"
    query_type = "$QUERY_TYPE"
    
    eval_request = {
        'participants': {
            'agent': purple_agent_url
        },
        'config': {
            'type': query_type
        }
    }
    
    request_text = json.dumps(eval_request)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
        from a2a.types import Message, Part, Role, TextPart
        
        resolver = A2ACardResolver(httpx_client=client, base_url=green_agent_url)
        agent_card = await resolver.get_agent_card()
        config = ClientConfig(httpx_client=client, streaming=False)
        factory = ClientFactory(config)
        a2a_client = factory.create(agent_card)
        
        message = Message(
            kind='message',
            role=Role.user,
            parts=[Part(root=TextPart(text=request_text))],
            message_id=uuid4().hex,
            context_id=None
        )
        
        events = []
        async for event in a2a_client.send_message(message):
            events.append(event)
            
            if isinstance(event, tuple):
                task, update = event
                print(f'Task ID: {task.id}')
                print(f'Task State: {task.status.state.value}')
                
                if task.status.message:
                    msg_text = task.status.message.parts[0].root.text if task.status.message.parts else ''
                    if msg_text:
                        print(f'Status: {msg_text}')
                
                if task.artifacts:
                    print(f'Artifacts: {len(task.artifacts)}')
                    for artifact in task.artifacts:
                        print(f'  - {artifact.name if hasattr(artifact, "name") else "unnamed"}')
        
        print(f'\nEvaluation completed! (Events: {len(events)})')

asyncio.run(evaluate())
PYTHON
