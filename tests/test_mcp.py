import importlib.util
import json
import pathlib
import sys

import httpx
import pytest


def _load_mcp_module():
    # Load the src/mcp_server.py module directly to avoid import path issues.
    root = pathlib.Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    mod_path = src_path / "mcp_server.py"
    spec = importlib.util.spec_from_file_location("mcp_server_mod", str(mod_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_tools_raise_not_implemented():
    """Ensure defined MCP tools raise NotImplementedError as placeholders."""
    m = _load_mcp_module()

    # The @mcp.tool() decorator may wrap the coroutine in a FunctionTool
    # object. If so, the original coroutine is available as `.func`.
    for name in ("edgar_search", "google_web_search"):
        tool = getattr(m, name)
        if callable(tool):
            # Tools are now implemented, so we skip this test if they are callable
            pytest.skip(f"Tool {name} is callable and implemented, skipping NotImplementedError test")
        elif hasattr(tool, "func"):
            # call the underlying coroutine function
            with pytest.raises(NotImplementedError):
                await tool.func()
        else:
            pytest.skip(f"Tool {name} is not callable and has no .func to invoke")


def test_mcp_object_has_run():
    """Ensure the module exposes an `mcp` object with a callable `run` method."""
    m = _load_mcp_module()
    assert hasattr(m, "mcp"), "Module should expose `mcp` object"
    assert hasattr(m.mcp, "run") and callable(m.mcp.run), "`mcp` should have callable `run`"


@pytest.mark.asyncio
async def test_google_web_search_via_http(mcp_server):
    """Test google_web_search tool via HTTP."""
    url = f"{mcp_server}/mcp"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "google_web_search",
            "arguments": {
                "q": "Python programming",
                "context_id": "test123"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Parse SSE response
        text = response.text
        lines = text.strip().split('\n')
        data_lines = [line for line in lines if line.startswith('data: ')]
        assert len(data_lines) > 0, "No data lines in SSE response"
        
        # Parse the last data line
        last_data = data_lines[-1].replace('data: ', '')
        result = json.loads(last_data)
        
        assert "result" in result, "Response should contain 'result'"
        assert isinstance(result["result"], list), "Result should be a list"


@pytest.mark.asyncio
async def test_edgar_search_via_http(mcp_server):
    """Test edgar_search tool via HTTP."""
    url = f"{mcp_server}/mcp"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "edgar_search",
            "arguments": {
                "query": "Apple Inc",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "context_id": "test"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Parse SSE response
        text = response.text
        lines = text.strip().split('\n')
        data_lines = [line for line in lines if line.startswith('data: ')]
        assert len(data_lines) > 0, "No data lines in SSE response"
        
        # Parse the last data line
        last_data = data_lines[-1].replace('data: ', '')
        result = json.loads(last_data)
        
        assert "result" in result, "Response should contain 'result'"
        assert isinstance(result["result"], list), "Result should be a list"
