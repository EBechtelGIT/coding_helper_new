"""Core agent with a custom async streaming agent loop."""

import asyncio
from typing import Callable, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage

from coding_agent.logging import AgentLogger
from coding_agent.permissions import Permissions


class CodingAgent:
    """The main coding agent with a custom streaming loop."""

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
        if not self.permissions.approval_callback:
            self.permissions.approval_callback = self._approval_callback

        filtered_tools = self._filter_tools(tools)
        self.tool_map = {t.name: t for t in filtered_tools}

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

        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.chat_history = []
        self.last_plan = ""
        self.llm = llm

    def _filter_tools(self, tools: list[BaseTool]) -> list[BaseTool]:
        """Filter tools based on permissions."""
        return [t for t in tools if self.permissions.can_use(t.name)]

    def _build_messages(self, user_input: str, messages: list = None) -> list:
        if messages:
            return messages
        msgs = [SystemMessage(content=self.system_prompt)]
        msgs.extend(self._tuples_to_messages(self.chat_history))
        msgs.append(HumanMessage(content=user_input))
        return msgs

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

    def _approval_callback(self, tool_name: str, args_str: str) -> bool:
        if self.permissions.approval_callback:
            return self.permissions.approval_callback(tool_name, args_str)
        return True

    # ------------------------------------------------------------------ #
    #  Sync API (backward-compatible, used by CLI mode & subagents)      #
    # ------------------------------------------------------------------ #

    def run_execution_turn(self, user_input: str) -> dict:
        """Run a turn in execution mode (temporarily disables planning)."""
        original_mode = self.planning_mode
        self.planning_mode = False
        try:
            result = self.run_turn(user_input)
        finally:
            self.planning_mode = original_mode
        return result

    def run_turn(self, user_input: str, messages: list = None) -> dict:
        """Run a single turn synchronously.

        Args:
            user_input: The user's message.
            messages: Optional pre-built message list (for subagents).

        Returns a dict with keys: response, tool_calls, messages, plan.
        """
        self.logger.log_turn_start(user_input)
        self.logger.log_separator()

        result = {"response": "", "tool_calls": [], "messages": [], "plan": ""}

        def on_event(event: dict):
            if event["type"] == "tool_call":
                result["tool_calls"].append({
                    "name": event["name"],
                    "params": str(event["args"]),
                    "result": "",
                })
            elif event["type"] == "tool_result":
                if result["tool_calls"]:
                    result["tool_calls"][-1]["result"] = event["result"][:500]
            elif event["type"] == "response":
                result["response"] = event["content"]

        self._run_loop(user_input, messages, on_event=on_event)

        if result["response"]:
            if messages is None:
                self.chat_history.append(("user", user_input))
                self.chat_history.append(("assistant", result["response"]))

        result["messages"] = []
        if self.planning_mode:
            result["plan"] = self.last_plan

        return result

    # ------------------------------------------------------------------ #
    #  Streaming API (async, used by the TUI)                             #
    # ------------------------------------------------------------------ #

    async def run_turn_streaming(
        self,
        user_input: str,
        messages: list = None,
        on_tool_call: Callable = None,
        on_tool_result: Callable = None,
        on_response: Callable = None,
        on_thinking: Callable = None,
    ) -> dict:
        """Run a turn with step-level streaming callbacks.

        Callbacks are invoked synchronously from a thread-pool executor;
        they should schedule UI work on the main thread (e.g. via
        ``App.call_from_thread`` or ``asyncio.run_coroutine_threadsafe``).
        """
        self.logger.log_turn_start(user_input)
        self.logger.log_separator()

        result = {"response": "", "tool_calls": [], "messages": [], "plan": ""}

        def on_event(event: dict):
            if event["type"] == "tool_call":
                result["tool_calls"].append({
                    "name": event["name"],
                    "params": str(event["args"]),
                    "result": "",
                })
                if on_tool_call:
                    on_tool_call(event["name"], event["args"])
            elif event["type"] == "tool_result":
                if result["tool_calls"]:
                    result["tool_calls"][-1]["result"] = event["result"][:500]
                if on_tool_result:
                    on_tool_result(event["name"], event["result"])
            elif event["type"] == "thinking":
                if on_thinking:
                    on_thinking(event["content"])
            elif event["type"] == "response":
                result["response"] = event["content"]
                if on_response:
                    on_response(event["content"])

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._run_loop, user_input, messages, on_event)

        if result["response"]:
            if messages is None:
                self.chat_history.append(("user", user_input))
                self.chat_history.append(("assistant", result["response"]))

        result["messages"] = []
        if self.planning_mode:
            result["plan"] = self.last_plan

        return result

    # ------------------------------------------------------------------ #
    #  Core loop (sync, shared by both APIs)                              #
    # ------------------------------------------------------------------ #

    def _run_loop(
        self,
        user_input: str,
        messages: list = None,
        on_event: Callable[[dict], None] = None,
    ):
        """Core synchronous agent loop shared by sync & streaming paths."""
        input_messages = self._build_messages(user_input, messages)
        step = 0

        while step < self.max_iterations:
            try:
                result = self.llm.invoke(input_messages)
            except Exception as e:
                if on_event:
                    on_event({"type": "response", "content": f"LLM call failed: {e}"})
                break

            tool_calls = []
            if hasattr(result, "tool_calls") and result.tool_calls:
                tool_calls = result.tool_calls

            if not tool_calls:
                response = result.content if hasattr(result, "content") else str(result)
                if on_event:
                    on_event({"type": "response", "content": response})
                break

            thinking = result.content if hasattr(result, "content") and result.content else ""
            if thinking and on_event:
                on_event({"type": "thinking", "content": thinking})

            for tc in tool_calls:
                name = tc.get("name", "unknown")
                args = tc.get("args", {})
                tc_id = tc.get("id", "")

                if on_event:
                    on_event({"type": "tool_call", "name": name, "args": args})

                if not self.permissions.can_use(name):
                    tool_output = f"Tool '{name}' is not permitted."
                elif name in self.tool_map:
                    try:
                        raw = self.tool_map[name].invoke(args)
                        tool_output = str(raw)
                    except Exception as e:
                        tool_output = f"Error executing {name}: {e}"
                else:
                    tool_output = f"Error: Tool '{name}' not found"

                if on_event:
                    on_event({"type": "tool_result", "name": name, "result": tool_output})

                input_messages.append(AIMessage(content="", tool_calls=[tc]))
                input_messages.append(
                    ToolMessage(content=str(tool_output)[:100000], tool_call_id=tc_id)
                )

            step += 1

        if self.planning_mode and not messages:
            self._extract_plan_from_messages(input_messages)

    def _extract_plan_from_messages(self, messages: list):
        for msg in messages:
            if hasattr(msg, "content") and any(
                kw in str(msg.content).lower()
                for kw in ["## goal", "## approach", "## current state"]
            ):
                self.last_plan = str(msg.content)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat_history = []

    def get_history(self) -> list:
        """Return the conversation history."""
        return list(self.chat_history)
