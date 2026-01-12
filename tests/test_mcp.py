import importlib.util
import pathlib
import sys

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

