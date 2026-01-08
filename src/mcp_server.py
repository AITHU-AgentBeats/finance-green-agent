from fastmcp import FastMCP

import logging
logger = logging.getLogger("MCP server")

mcp = FastMCP(
    name="MCP Server",
    version="1.0.0",
    instructions="Tools for Purple agents to be used",
    stateless_http=True,
)


@mcp.tool()
async def edgar_search() -> dict:
    """
    Search SEC EDGAR database.
    """
    raise NotImplementedError


@mcp.tool()
async def google_web_search() -> dict:
    """
    Search the web using SerpAPI
    """
    raise NotImplementedError

# Launch MCP server
def run_server(host: str = "127.0.0.1", port: int = 8001):
    """
    Run the MCP server
    """
    logger.info(f"Starting MCP server on {host}:{port}")

    try:
        mcp.run(host=host, port=port, transport="http")
    except Exception as e:
        logger.error(f"MCP server failed: {e}")
        raise


# ===== Standalone Execution =====

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind")
    args = parser.parse_args()

    logger.info(f"Starting MCP server on http://{args.host}:{args.port}")
    run_server(host=args.host, port=args.port)
