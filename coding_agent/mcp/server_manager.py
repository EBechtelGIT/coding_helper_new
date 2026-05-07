"""Manager for multiple MCP servers."""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from coding_agent.mcp.client import MCPServerConnection, MCPTool


class MCPServerManager:
    """Manages multiple MCP server connections."""

    def __init__(self, config_path: Optional[str] = None):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.config_path = config_path or self._default_config_path()
        self._tools_cache: List[MCPTool] = []

    def _default_config_path(self) -> str:
        """Get the default config path."""
        # Check project config first
        project_config = Path.cwd() / ".opencode" / "mcp.json"
        if project_config.exists():
            return str(project_config)

        # Fall back to global config
        home = Path.home()
        global_config = home / ".config" / "opencode" / "mcp.json"
        if global_config.exists():
            return str(global_config)

        return str(project_config)  # Return project path even if it doesn't exist

    def load_config(self) -> Dict[str, Any]:
        """Load MCP server configuration."""
        if not os.path.exists(self.config_path):
            return {}

        with open(self.config_path, "r") as f:
            config = json.load(f)

        return config.get("mcpServers", {})

    def save_config(self, config: Dict[str, Any]):
        """Save MCP server configuration."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({"mcpServers": config}, f, indent=2)

    async def add_server(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> List[MCPTool]:
        """Add and connect to a new MCP server."""
        connection = MCPServerConnection(
            name=name,
            command=command,
            args=args,
            env=env,
        )

        tools = await connection.connect()
        self.servers[name] = connection
        self._tools_cache.extend(tools)

        # Update config
        config = self.load_config()
        config[name] = {
            "command": command,
            "args": args,
            **({"env": env} if env else {}),
        }
        self.save_config(config)

        return tools

    async def remove_server(self, name: str):
        """Remove and disconnect from an MCP server."""
        if name in self.servers:
            await self.servers[name].disconnect()
            del self.servers[name]

            # Update config
            config = self.load_config()
            if name in config:
                del config[name]
                self.save_config(config)

    async def get_all_tools(self) -> List[MCPTool]:
        """Get all tools from all connected servers."""
        if not self._tools_cache:
            await self._refresh_tools()
        return self._tools_cache

    async def _refresh_tools(self):
        """Refresh the tools cache from all servers."""
        self._tools_cache = []
        for connection in self.servers.values():
            self._tools_cache.extend(connection.get_tools())

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool by name (format: server_name__tool_name)."""
        # Parse server and tool name
        parts = tool_name.split("__", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid MCP tool name: {tool_name}. Expected format: server__tool")

        server_name, actual_tool_name = parts
        if server_name not in self.servers:
            raise ValueError(f"MCP server not found: {server_name}")

        return await self.servers[server_name].call_tool(actual_tool_name, arguments)

    async def connect_all(self) -> List[MCPTool]:
        """Connect to all servers defined in config."""
        config = self.load_config()
        all_tools = []

        for name, server_config in config.items():
            command = server_config["command"]
            args = server_config.get("args", [])
            env = server_config.get("env")

            try:
                connection = MCPServerConnection(
                    name=name,
                    command=command,
                    args=args,
                    env=env,
                )
                tools = await connection.connect()
                self.servers[name] = connection
                all_tools.extend(tools)
            except Exception as e:
                print(f"Failed to connect to MCP server {name}: {e}")

        self._tools_cache = all_tools
        return all_tools

    async def disconnect_all(self):
        """Disconnect from all servers."""
        for connection in self.servers.values():
            await connection.disconnect()
        self.servers.clear()
        self._tools_cache.clear()
