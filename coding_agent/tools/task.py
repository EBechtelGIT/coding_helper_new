"""Task tool for invoking subagents (Feature 2: equivalent to OpenCode's Task tool)."""

import json
import re
from typing import Optional, Dict, Any, List
from langchain.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage


def create_task_tool(subagent_runner, current_agent_name: str = "build"):
    """Create the run_task tool for invoking subagents.
    
    This allows primary agents to delegate work to subagents like @general or @explore.
    Similar to OpenCode's Task tool that lets agents spawn subagents.
    """
    
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
        # Validate subagent name
        valid_subagents = ["general", "explore", "build", "plan"]
        if subagent not in valid_subagents:
            return f"Error: Unknown subagent '{subagent}'. Valid options: {', '.join(valid_subagents)}"
        
        # Prepare the message
        message = f"[Task delegated to @{subagent}]\n\n{task_description}"
        if images:
            message += f"\n\nImages: {', '.join(images)}"
        
        try:
            # Invoke the subagent
            result = subagent_runner.run_subagent(
                agent_name=subagent,
                message=message,
                parent_agent=current_agent_name,
            )
            
            # Format the result
            if isinstance(result, dict):
                response = result.get("response", str(result))
                tool_calls = result.get("tool_calls", [])
                
                output = f"[@{subagent} response]\n{response}"
                if tool_calls:
                    output += f"\n\nTools used: {len(tool_calls)}"
                return output
            return str(result)
            
        except Exception as e:
            return f"Error invoking subagent @{subagent}: {str(e)}"
    
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


def get_task_tool(subagent_runner, current_agent_name: str = "build") -> Tool:
    """Get the run_task tool for the current agent."""
    return create_task_tool(subagent_runner, current_agent_name)


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
