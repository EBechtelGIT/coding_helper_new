"""Adapter to convert MCP tools to LangChain tools."""

import asyncio
import threading
from typing import Dict, Any, List, Optional

from langchain_core.tools import Tool

from coding_agent.mcp.client import MCPTool
from coding_agent.mcp.server_manager import MCPServerManager


class MCPToolAdapter:
    """Adapts MCP tools to LangChain tools with dynamic execution."""

    def __init__(self, server_manager: MCPServerManager):
        self._server_manager = server_manager

    def adapt_tool(self, mcp_tool: MCPTool) -> Tool:
        """Convert an MCP tool to a LangChain Tool."""
        tool_name = f"mcp_{mcp_tool.server_name}__{mcp_tool.name}"

        def sync_func(**kwargs) -> str:
            try:
                loop = asyncio.get_running_loop()
                # Loop is running - run in a new thread with its own loop
                result = []
                exception = []

                def _run():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        r = new_loop.run_until_complete(
                            self._call_tool_async(mcp_tool.name, mcp_tool.server_name, kwargs)
                        )
                        result.append(r)
                    except Exception as e:
                        exception.append(e)
                    finally:
                        new_loop.close()

                t = threading.Thread(target=_run, daemon=True)
                t.start()
                t.join(timeout=120)
                if exception:
                    return f"MCP error: {exception[0]}"
                return result[0] if result else "MCP tool returned no result"
            except RuntimeError:
                return asyncio.run(
                    self._call_tool_async(mcp_tool.name, mcp_tool.server_name, kwargs)
                )

        async def async_func(**kwargs) -> str:
            return await self._call_tool_async(mcp_tool.name, mcp_tool.server_name, kwargs)

        return Tool(
            name=tool_name,
            description=f"[MCP:{mcp_tool.server_name}] {mcp_tool.description}",
            func=sync_func,
            coroutine=async_func,
            args_schema=mcp_tool.input_schema if mcp_tool.input_schema else None,
        )

    async def _call_tool_async(
        self, tool_name: str, server_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Call an MCP tool asynchronously."""
        full_tool_name = f"{server_name}__{tool_name}"
        return await self._server_manager.call_tool(full_tool_name, arguments)

    def get_all_langchain_tools(self) -> List[Tool]:
        """Get all MCP tools adapted as LangChain tools."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    mcp_tools = new_loop.run_until_complete(
                        self._server_manager.get_all_tools()
                    )
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(loop)
            else:
                mcp_tools = loop.run_until_complete(
                    self._server_manager.get_all_tools()
                )
        except RuntimeError:
            mcp_tools = asyncio.run(
                self._server_manager.get_all_tools()
            )

        return [self.adapt_tool(tool) for tool in mcp_tools]
