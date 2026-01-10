import aiohttp
from fastmcp import FastMCP

from config import settings

import logging
logger = logging.getLogger("MCP server")

mcp = FastMCP(
    name="MCP Server",
    version="1.0.0",
    instructions="Tools for Purple agents to be used",
    stateless_http=True,
)


@mcp.tool()
async def edgar_search(query: str, start_date:str, end_date:str, context_id: str = None) -> list:
    """
    Search SEC EDGAR database.
    """
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

    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json=payload, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()

    filings = result.get("filings", [])
    return filings


@mcp.tool()
async def google_web_search(q:str, context_id: str = "default") -> list[dict]:
    """
    Search the web using SerpAPI
    """
    # Fill search params
    params = {
        "api_key": settings.SERPAPI_API_KEY,
        "engine": "google",
        "q": q,
    }

    result = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://serpapi.com/search.json", params=params) as response:
            response.raise_for_status()
            result = await response.json()

    if result:
        return result.get("organic_results", [])
    # Else
    return []

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
