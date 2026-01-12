import argparse
import uvicorn
import threading

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentCardSignature,
    AgentSkill,
)
from mcp_server import run_server
from executor import Executor
from config import logger


def main():
    parser = argparse.ArgumentParser(description="Run the A2A agent.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="URL to advertise in the agent card")
    parser.add_argument("--mcp-port", type=int, default=9020, help="MCP server port (0 to disable MCP)")
    parser.add_argument("--data-path", type=str, default="data/public.csv", help="Path to dataset")
    args = parser.parse_args()

    # Fill in your agent card
    # See: https://a2a-protocol.org/latest/tutorials/python/3-agent-skills-and-card/

    skill = AgentSkill(
        id="assess",
        name="Finance benchmark assessment agent",
        description="Assess correct responses and serves tools as skills.",
        tags=["green agent", "assessment hosting", "finance benchmark"],
        examples=[
            '''{
                    "participants" : {"agent": "http://localhost:9019"}, 
                    "config" : {"type" : "all"}
                }
            '''
        ]
    )

    # Standard A2A method signatures
    signatures = [
        AgentCardSignature(signature="message/send", protected="false"),
        AgentCardSignature(signature="message/stream", protected="false"),
        AgentCardSignature(signature="tasks/get", protected="false"),
        AgentCardSignature(signature="tasks/cancel", protected="false"),
    ]

    agent_card = AgentCard(
        name="Finance Benchmark Green Agent",
        description="Agent for agent assessment over the finance benchamrk dataset",
        url=args.card_url or f"http://{args.host}:{args.port}/",
        version='0.1.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        signatures=signatures
    )

    request_handler = DefaultRequestHandler(
        agent_executor=Executor(),
        task_store=InMemoryTaskStore(),
    )
    agent_server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    # Init the MCP server (independent thread)
    logger.info("Initializing MCP server...")
    mcp_thread = threading.Thread(target=run_server, daemon=True, name="MCP", args=[args.host, args.mcp_port])
    mcp_thread.start()

    # Init main app
    logger.info("Initializing Agent server...")
    uvicorn.run(agent_server.build(), host=args.host, port=args.port)

if __name__ == '__main__':
    main()
