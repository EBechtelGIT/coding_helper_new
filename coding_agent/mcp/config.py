"""MCP server configuration loader.

Supports both project-level (.opencode/mcp.json) and 
global-level (~/.config/opencode/mcp.json) configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_mcp_config(project_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load MCP server configuration from all config locations.
    
    Args:
        project_dir: Project directory to look for .opencode/mcp.json
        
    Returns:
        Dict with 'mcpServers' key containing server configs
    """
    configs = []
    
    # 1. Global config: ~/.config/opencode/mcp.json
    home = Path.home()
    global_config = home / ".config" / "opencode" / "mcp.json"
    if global_config.exists():
        try:
            with open(global_config, 'r') as f:
                configs.append(json.load(f))
        except Exception:
            pass
    
    # 2. Project config: <project>/.opencode/mcp.json
    if project_dir:
        project_config = Path(project_dir) / ".opencode" / "mcp.json"
    else:
        project_config = Path.cwd() / ".opencode" / "mcp.json"
    
    if project_config.exists():
        try:
            with open(project_config, 'r') as f:
                configs.append(json.load(f))
        except Exception:
            pass
    
    # Merge configs (project overrides global)
    merged = {"mcpServers": {}}
    for config in configs:
        servers = config.get("mcpServers", {})
        merged["mcpServers"].update(servers)
    
    return merged


def save_mcp_config(config: Dict[str, Any], global_config: bool = False) -> bool:
    """Save MCP server configuration.
    
    Args:
        config: Config dict with 'mcpServers' key
        global_config: If True, save to global config location
        
    Returns:
        True if successful
    """
    if global_config:
        config_dir = Path.home() / ".config" / "opencode"
    else:
        config_dir = Path.cwd() / ".opencode"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "mcp.json"
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def add_mcp_server(
    name: str,
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None,
    global_config: bool = False,
) -> bool:
    """Add an MCP server to the configuration.
    
    Args:
        name: Server name
        command: Command to run (e.g., 'npx', 'uvx')
        args: Arguments for the command
        env: Optional environment variables
        global_config: If True, save to global config
        
    Returns:
        True if successful
    """
    config = load_mcp_config()
    
    server_config = {
        "command": command,
        "args": args,
    }
    if env:
        server_config["env"] = env
    
    config["mcpServers"][name] = server_config
    
    return save_mcp_config(config, global_config)


def remove_mcp_server(name: str, global_config: bool = False) -> bool:
    """Remove an MCP server from configuration."""
    config = load_mcp_config()
    
    if name in config["mcpServers"]:
        del config["mcpServers"][name]
        return save_mcp_config(config, global_config)
    
    return False


def list_mcp_servers(project_dir: Optional[str] = None) -> List[str]:
    """List configured MCP server names."""
    config = load_mcp_config(project_dir)
    return list(config.get("mcpServers", {}).keys())
