"""MCP client for connecting to external tool servers."""

import asyncio
import json
from typing import Optional, Dict, Any, List
import subprocess
from contextlib import asynccontextmanager

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    MCP_AVAILABLE = False


class MCPTool:
    """A tool exposed by an MCP server."""

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], server_name: str):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name

    def to_langchain_tool(self):
        """Convert to a LangChain tool."""
        from langchain.tools import Tool

        async def execute(**kwargs) -> str:
            # This will be handled by the server manager
            raise NotImplementedError("Use MCPToolAdapter instead")

        return Tool(
            name=f"mcp_{self.server_name}_{self.name}",
            description=f"[MCP:{self.server_name}] {self.description}",
            func=None,  # Will be set by adapter
            coroutine=execute,
        )


class MCPServerConnection:
    """Manages connection to a single MCP server."""

    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self._session: Optional[ClientSession] = None
        self._tools: List[MCPTool] = []
        self._process: Optional[subprocess.Popen] = None
        self._read = None
        self._write = None
        self._stdio_transport = None
        if not MCP_AVAILABLE:
            raise ImportError("MCP package not installed. Install with: pip install mcp")

    async def connect(self) -> List[MCPTool]:
        """Connect to the server and list available tools."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**self.env, **dict(self._get_default_env())},
        )

        self._stdio_transport = stdio_client(server_params)
        self._read, self._write = await self._stdio_transport.__aenter__()

        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()

        tools_result = await self._session.list_tools()
        self._tools = [
            MCPTool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                server_name=self.name,
            )
            for tool in tools_result.tools
        ]
        return self._tools

    def _get_default_env(self) -> Dict[str, str]:
        """Get default environment variables."""
        import os
        return {k: v for k, v in os.environ.items() if k.startswith("PATH")}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on this server."""
        if not self._session:
            raise RuntimeError(f"Not connected to MCP server {self.name}")

        result = await self._session.call_tool(tool_name, arguments)
        return result.content if isinstance(result.content, str) else json.dumps(result.content)

    def get_tools(self) -> List[MCPTool]:
        """Get the list of available tools."""
        return self._tools

    async def disconnect(self):
        """Disconnect from the server."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
        if self._stdio_transport:
            try:
                await self._stdio_transport.__aexit__(None, None, None)
            except Exception:
                pass
            self._stdio_transport = None
            self._read = None
            self._write = None
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception:
                pass
            self._process = None
