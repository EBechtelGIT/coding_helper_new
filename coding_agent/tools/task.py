"""Task tool for invoking subagents (Feature 2: equivalent to OpenCode's Task tool)."""

import json
import re
from typing import Optional, Dict, Any, List
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage


def create_task_tool(subagent_runner, current_agent_name: str = "build", create_agent_fn=None):
    """Create the run_task tool for invoking subagents.
    
    This allows primary agents to delegate work to subagents like @general or @explore.
    Similar to OpenCode's Task tool that lets agents spawn subagents.
    """
    from coding_agent.config import load_config
    
    def run_task(
        task_description: str,
        subagent: str = "general",
        images: Optional[List[str]] = None,
    ) -> str:
        """Invoke a subagent to handle a specific task.
        
        Args:
            task_description: Description of the task for the subagent
            subagent: Name of the subagent to invoke (general, explore, etc.)
            images: Optional list of image paths for multimodal tasks
            
        Returns:
            Result from the subagent's execution
        """
        valid_subagents = ["general", "explore", "build", "plan"]
        if subagent not in valid_subagents:
            return f"Error: Unknown subagent '{subagent}'. Valid options: {', '.join(valid_subagents)}"
        
        config = load_config()
        agent_config = config.agents.get(subagent)
        if not agent_config:
            return f"Error: Subagent configuration not found for '{subagent}'"
        
        try:
            if hasattr(subagent_runner, 'spawn') and callable(subagent_runner.spawn):
                result = subagent_runner.spawn(
                    agent_config=agent_config,
                    task=task_description,
                    create_agent_fn=create_agent_fn,
                )
            else:
                return f"[@{subagent}] Subagent spawning not available.\nTask: {task_description}"
            
            if hasattr(result, 'result'):
                output = f"[@{subagent} response]\n{result.result}"
                if result.tool_calls:
                    output += f"\n\nTools used: {len(result.tool_calls)}"
                return output
            
            if isinstance(result, dict):
                response_text = result.get("result", result.get("response", str(result)))
                tool_calls = result.get("tool_calls", [])
                output = f"[@{subagent} response]\n{response_text}"
                if tool_calls:
                    output += f"\n\nTools used: {len(tool_calls)}"
                return output
            
            return str(result)
            
        except Exception as e:
            return f"[@{subagent}] Subagent not available: {str(e)}.\nTask: {task_description}"
    
    return Tool(
        name="run_task",
        description="""Invoke a subagent to handle a specific task.
        
        Use this when you need to:
        - Research complex questions that require multiple steps
        - Explore a codebase without affecting the main conversation
        - Run tasks in parallel using different agents
        
        Available subagents:
        - general: Full-access agent for research and multi-step tasks
        - explore: Read-only agent for fast codebase exploration
        - build: Default agent with full tool access
        - plan: Restricted agent for planning without changes
        
        Args:
            task_description: What the subagent should do
            subagent: Which subagent to use (default: general)
            images: Optional list of image paths for multimodal tasks
        """,
        func=run_task,
    )


def get_task_tool(subagent_runner, current_agent_name: str = "build", create_agent_fn=None) -> Tool:
    """Get the run_task tool for the current agent."""
    return create_task_tool(subagent_runner, current_agent_name, create_agent_fn)


# Update the TOOL_CATEGORIES to include task
TOOL_CATEGORIES = {
    "read": {"read_file"},
    "edit": {"write_file", "edit_file", "apply_patch"},
    "glob": {"glob_search"},
    "grep": {"grep_search"},
    "list": {"list_files"},
    "bash": {"run_bash"},
    "task": {"run_task"},
    "web": {"web_search", "web_fetch"},
    "todo": {"todowrite", "todoread"},
    "git": {"run_git"},
    "python": {"run_python"},
}
