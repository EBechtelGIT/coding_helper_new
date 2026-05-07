"""Core agent using langchain's create_agent with multi-agent support."""

from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage, AIMessage, SystemMessage, HumanMessage

from coding_agent.logging import AgentLogger
from coding_agent.permissions import Permissions


class CodingAgent:
    """The main coding agent powered by LangGraph."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: list[BaseTool],
        max_iterations: int = 10,
        verbose: bool = False,
        planning_mode: bool = False,
        plan_file: str = "PLAN.md",
        system_prompt: str = "",
        permissions: Permissions = None,
    ):
        self.logger = AgentLogger(verbose=verbose)

        self.planning_mode = planning_mode
        self.plan_file = plan_file

        self.permissions = permissions or Permissions()
        self.permissions.approval_callback = self._approval_callback

        filtered_tools = self._filter_tools(tools)

        if not system_prompt:
            if planning_mode:
                system_prompt = (
                    "You are a helpful coding assistant in PLANNING MODE. "
                    "Use ONLY read-only tools (read_file, glob_search, grep_search, web_search) "
                    "to analyze the codebase. DO NOT use write_file, edit_file, run_bash, or run_python. "
                    "Create a structured plan with these sections:\n"
                    "# Plan\n"
                    "## Goal\n<what we're building and why>\n"
                    "## Current State\n<what exists now, relevant files>\n"
                    "## Approach\n<step-by-step implementation plan>\n"
                    "## Files to Modify\n<list of files>\n"
                    "## Risks\n<what could go wrong>\n"
                    "## Open Questions\n<things to clarify>\n"
                )
            else:
                system_prompt = (
                    "You are a helpful coding assistant. Use tools when needed to complete tasks."
                )

        self.agent = create_agent(
            model=llm,
            tools=filtered_tools,
            system_prompt=system_prompt,
        )
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.chat_history = []
        self.last_plan = ""
        self.llm = llm

    def _filter_tools(self, tools: list[BaseTool]) -> list[BaseTool]:
        """Filter tools based on permissions."""
        return [t for t in tools if self.permissions.can_use(t.name)]

    @staticmethod
    def _tuples_to_messages(tuples_list: list) -> list:
        messages = []
        for role, content in tuples_list:
            if role in ("user", "human"):
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def _chat_history_to_messages(self) -> list:
        return self._tuples_to_messages(self.chat_history)

    def _approval_callback(self, tool_name: str, args_str: str) -> bool:
        """Approval callback for tools that need user confirmation."""
        if self.permissions.approval_callback:
            return self.permissions.approval_callback(tool_name, args_str)
        return True

    def run_turn(self, user_input: str, messages: list = None) -> dict:
        """Run a single turn and return structured result.

        Args:
            user_input: The user's message.
            messages: Optional pre-built message list (for subagents).

        Returns a dict with keys:
            - response (str): The agent's final text response
            - tool_calls (list[dict]): Each dict has 'name', 'params', 'result'
            - messages (list): Raw message history from the agent
            - plan (str): Plan content if in planning mode
        """
        self.logger.log_turn_start(user_input)
        self.logger.log_separator()

        config = {"recursion_limit": self.max_iterations * 2 + 5}

        if messages is not None:
            input_messages = messages
        else:
            input_messages = self._chat_history_to_messages() + [HumanMessage(content=user_input)]

        result = self.agent.invoke(
            {
                "messages": input_messages,
            },
            config=config,
        )

        tool_calls = self._extract_tool_calls(result)
        response = result.get("structured_response") or self._extract_response(result)
        plan_content = self._extract_plan(result) if self.planning_mode else ""

        if plan_content:
            self.last_plan = plan_content

        if messages is None:
            self.chat_history.append(("user", user_input))
            self.chat_history.append(("assistant", response))

        return {
            "response": response,
            "tool_calls": tool_calls,
            "messages": result.get("messages", []),
            "plan": plan_content,
        }

    def run_execution_turn(self, user_input: str) -> dict:
        """Run a turn in execution mode (after planning approved)."""
        original_mode = self.planning_mode
        self.planning_mode = False

        try:
            result = self.run_turn(user_input)
        finally:
            self.planning_mode = original_mode

        return result

    def _extract_tool_calls(self, result: dict) -> list[dict]:
        """Extract tool calls and their results from agent messages."""
        tool_calls = []
        messages = result.get("messages", [])

        for i, msg in enumerate(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    tool_args = tc.get("args", {})
                    result_text = ""
                    if i + 1 < len(messages) and isinstance(messages[i + 1], ToolMessage):
                        result_text = str(messages[i + 1].content)[:500]
                    tool_calls.append({
                        "name": tool_name,
                        "params": str(tool_args),
                        "result": result_text,
                    })
        return tool_calls

    def _extract_response(self, result: dict) -> str:
        """Extract the response string from the agent result."""
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                return str(last_msg.content)
            return str(last_msg)
        return str(result)

    def _extract_plan(self, result: dict) -> str:
        """Extract plan content from agent messages."""
        messages = result.get("messages", [])
        plan_sections = []

        for msg in messages:
            if not hasattr(msg, 'content'):
                continue
            content = str(msg.content)
            if any(keyword in content.lower() for keyword in ['## goal', '## approach', '## current state']):
                plan_sections.append(content)

        if plan_sections:
            return "\n\n".join(plan_sections)
        return ""

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat_history = []

    def get_history(self) -> list:
        """Return the conversation history."""
        return list(self.chat_history)
