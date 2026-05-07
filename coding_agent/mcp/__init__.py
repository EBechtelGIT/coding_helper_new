"""MCP (Model Context Protocol) integration for the coding agent."""

from coding_agent.mcp.client import MCPTool, MCPServerConnection
from coding_agent.mcp.server_manager import MCPServerManager
from coding_agent.mcp.tool_adapter import MCPToolAdapter

__all__ = [
    "MCPTool",
    "MCPServerConnection",
    "MCPServerManager",
    "MCPToolAdapter",
]
