import aiohttp
import asyncio
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
    logger.debug(f"[MCP TOOL CALL] edgar_search")
    logger.debug(
        f"[MCP TOOL CALL] Parameters: query='{query}', start_date='{start_date}', end_date='{end_date}', context_id='{context_id}'"
    )

    # Check if API key is configured
    if not settings.EDGAR_API_KEY:
        error_msg = "[MCP TOOL CALL] edgar_search - Error: EDGAR_API_KEY not configured. Please set EDGAR_API_KEY in .env file"
        logger.error(error_msg)
        raise ValueError(error_msg)

    api_url = "https://api.sec-api.io/full-text-search"

    # sec-api.io expects the API key directly in Authorization header (not Bearer token)
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

    # Retry configuration for rate limiting
    max_retries = 3
    base_delay = 2  # seconds
    max_delay = 60  # seconds

    for attempt in range(max_retries):
        try:
            logger.debug(f"[MCP TOOL CALL] edgar_search - Calling API: {api_url} (attempt {attempt + 1}/{max_retries})")
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    # Handle rate limiting (429) with exponential backoff
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", base_delay * (2 ** attempt)))
                        delay = min(retry_after, max_delay)
                        
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"[MCP TOOL CALL] edgar_search - Rate limited (429). "
                                f"Retrying after {delay} seconds (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_msg = f"[MCP TOOL CALL] edgar_search - Rate limited (429) after {max_retries} attempts. Please wait before retrying."
                            logger.error(error_msg)
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=429,
                                message="Too Many Requests - Rate limit exceeded"
                            )
                    
                    # Handle other HTTP errors (but not 429, which is handled above)
                    if response.status >= 400 and response.status != 429:
                        error_text = await response.text()
                        error_msg = f"[MCP TOOL CALL] edgar_search - API error {response.status}: {error_text}"
                        logger.error(error_msg)
                        response.raise_for_status()
                    
                    # Read response JSON only if status is OK
                    result = await response.json()

            filings = result.get("filings", [])
            logger.debug(f"[MCP TOOL CALL] edgar_search - Success: Found {len(filings)} filings")
            logger.debug(
                f"[MCP TOOL CALL] edgar_search - First filing: {filings[0] if filings else 'None'}"
            )
            return filings
            
        except aiohttp.ClientResponseError as e:
            # Re-raise rate limiting errors after all retries exhausted
            if e.status == 429:
                raise
            # For other HTTP errors, log and raise
            logger.error(f"[MCP TOOL CALL] edgar_search - HTTP error {e.status}: {e.message}")
            raise
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"[MCP TOOL CALL] edgar_search - Timeout. Retrying after {delay} seconds (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
                continue
            else:
                error_msg = "[MCP TOOL CALL] edgar_search - Timeout after multiple retries"
                logger.error(error_msg)
                raise
        except Exception as e:
            logger.error(f"[MCP TOOL CALL] edgar_search - Error: {e}")
            raise
    
    # Should not reach here, but just in case
    raise Exception(f"[MCP TOOL CALL] edgar_search - Failed after {max_retries} attempts")


@mcp.tool()
async def google_web_search(q: str, context_id: str = "default") -> list[dict]:
    """
    Search the web using SerpAPI
    """
    logger.debug(f"[MCP TOOL CALL] google_web_search")
    logger.debug(f"[MCP TOOL CALL] Parameters: q='{q}', context_id='{context_id}'")

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
            logger.debug(
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
