"""
MCP ↔ Anthropic tool format bridge.

Spawns the MCP server as a subprocess, keeps a persistent async session in a
background thread, and exposes a synchronous API that tutor_brain.py can call.
"""
import asyncio
import json
import sys
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ── Background event loop (keeps MCP session alive) ──────────────────────────

_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()


def _run(coro, timeout: int = 30):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=timeout)


# ── Session bootstrap ─────────────────────────────────────────────────────────

_session: ClientSession | None = None
_exit_stack: AsyncExitStack | None = None


async def _connect():
    global _session, _exit_stack
    _exit_stack = AsyncExitStack()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "core.mcp_server"]
    )
    read, write = await _exit_stack.enter_async_context(stdio_client(server_params))
    _session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()


try:
    _run(_connect())
except Exception as e:
    raise RuntimeError(
        f"Failed to start MCP tool server: {e}\n"
        "Make sure you are running from the project root: streamlit run app.py"
    ) from e

# ── Convert MCP tool schema → Anthropic format ────────────────────────────────

def _to_anthropic(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema,
    }


_mcp_tools = _run(_session.list_tools()).tools       # type: ignore[union-attr]
TOOLS_ANTHROPIC: list[dict] = [_to_anthropic(t) for t in _mcp_tools]

# ── Public API ────────────────────────────────────────────────────────────────

def execute_tool(name: str, args: dict) -> str:
    async def _call():
        result = await _session.call_tool(name, args)   # type: ignore[union-attr]
        if result.content:
            return result.content[0].text
        return json.dumps({"error": "No result"})
    return _run(_call())
