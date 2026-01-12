import httpx
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--agent-url",
        default="http://localhost:9009",
        help="Agent URL (default: http://localhost:9009)",
    )
    parser.addoption(
        "--mcp-url",
        default="http://localhost:9020",
        help="MCP Server URL (default: http://localhost:9020)",
    )


@pytest.fixture(scope="session")
def agent(request):
    """Agent URL fixture. Agent must be running before tests start."""
    url = request.config.getoption("--agent-url")

    try:
        response = httpx.get(f"{url}/.well-known/agent-card.json", timeout=2)
        if response.status_code != 200:
            pytest.exit(f"Agent at {url} returned status {response.status_code}", returncode=1)
    except Exception as e:
        pytest.exit(f"Could not connect to agent at {url}: {e}", returncode=1)

    return url


@pytest.fixture(scope="session")
def mcp_server(request):
    """MCP Server URL fixture. MCP server must be running before tests start."""
    url = request.config.getoption("--mcp-url")
    try:
        response = httpx.get(f"{url}/.well-known/mcp-card.json", timeout=2)
        if response.status_code != 200:
            pytest.exit(f"MCP Server at {url} returned status {response.status_code}", returncode=1)
    except Exception as e:
        pytest.exit(f"Could not connect to MCP Server at {url}: {e}", returncode=1)
    return url
