"""Adapter to convert MCP tools to LangChain tools."""

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
            """Synchronous wrapper for the async tool call."""
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop for this call
                return asyncio.get_event_loop().run_until_complete(
                    self._call_tool_async(mcp_tool.name, mcp_tool.server_name, kwargs)
                )
            else:
                return asyncio.run(
                    self._call_tool_async(mcp_tool.name, mcp_tool.server_name, kwargs)
                )

        async def async_func(**kwargs) -> str:
            """Async function for tool call."""
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
        import asyncio
        # Get all MCP tools
        mcp_tools = asyncio.get_event_loop().run_until_complete(
            self._server_manager.get_all_tools()
        )

        # Adapt each tool
        return [self.adapt_tool(tool) for tool in mcp_tools]
