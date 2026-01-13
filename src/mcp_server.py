import aiohttp
import json
import time
from fastmcp import FastMCP

from config import settings, logger

mcp = FastMCP(
    name="MCP Server",
    version="1.0.0",
    instructions="Tools for Purple agents to be used",
    stateless_http=True,
)


@mcp.tool()
async def edgar_search(query: str, start_date: str, end_date: str, context_id: str = None) -> list:
    """
    Search SEC EDGAR database.
    """
    logger.info(f"[MCP TOOL CALL] edgar_search")
    logger.info(
        f"[MCP TOOL CALL] Parameters: query='{query}', start_date='{start_date}', end_date='{end_date}', context_id='{context_id}'"
    )

    api_url = "https://api.sec-api.io/full-text-search"

    headers = {
        "Content-Type": "application/json",
        "Authorization": settings.EDGAR_API_KEY,
    }

    payload = {
        "query": query,
        "formTypes": [],
        "ciks": [],
        "startDate": start_date,
        "endDate": end_date,
        "page": 1,
    }

    try:
        logger.debug(f"[MCP TOOL CALL] edgar_search - Calling API: {api_url}")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()

        filings = result.get("filings", [])
        logger.info(f"[MCP TOOL CALL] edgar_search - Success: Found {len(filings)} filings")
        logger.debug(
            f"[MCP TOOL CALL] edgar_search - First filing: {filings[0] if filings else 'None'}"
        )
        return filings
    except Exception as e:
        logger.error(f"[MCP TOOL CALL] edgar_search - Error: {e}")
        raise


@mcp.tool()
async def google_web_search(q: str, context_id: str = "default") -> list[dict]:
    """
    Search the web using SerpAPI
    """
    logger.info(f"[MCP TOOL CALL] google_web_search")
    logger.info(f"[MCP TOOL CALL] Parameters: q='{q}', context_id='{context_id}'")

    # Fill search params
    params = {
        "api_key": settings.SERPAPI_API_KEY,
        "engine": "google",
        "q": q,
    }

    try:
        logger.debug(f"[MCP TOOL CALL] google_web_search - Calling SerpAPI")
        result = []
        async with aiohttp.ClientSession() as session:
            async with session.get("https://serpapi.com/search.json", params=params) as response:
                response.raise_for_status()
                result = await response.json()

        if result:
            organic_results = result.get("organic_results", [])
            logger.info(
                f"[MCP TOOL CALL] google_web_search - Success: Found {len(organic_results)} results"
            )
            logger.debug(
                f"[MCP TOOL CALL] google_web_search - First result: {organic_results[0].get('title', 'N/A') if organic_results else 'None'}"
            )
            return organic_results
        # Else
        logger.warning(f"[MCP TOOL CALL] google_web_search - No results returned")
        return []
    except Exception as e:
        logger.error(f"[MCP TOOL CALL] google_web_search - Error: {e}")
        raise


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9020, help="Port to bind")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
