"""Core agent with a custom async streaming agent loop."""

import asyncio
from typing import Callable, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage, BaseMessage

from coding_agent.logging import AgentLogger
from coding_agent.permissions import Permissions


DOOM_LOOP_THRESHOLD = 3  # Same tool+args repeated this many times = stuck


class CodingAgent:
    """The main coding agent with a custom streaming loop."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: list[BaseTool],
        max_iterations: int = 25,
        verbose: bool = False,
        planning_mode: bool = False,
        plan_file: str = "PLAN.md",
        system_prompt: str = "",
        permissions: Permissions = None,
        doom_loop_threshold: int = 3,
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
                    "Your job is to analyze the codebase and produce a concrete, actionable plan.\n\n"
                    "RULES:\n"
                    "- Use read-only tools (read_file, glob_search, grep_search, web_search) to investigate.\n"
                    "- DO NOT use write_file, edit_file, run_bash, or run_python.\n"
                    "- Share your findings and observations as you go.\n"
                    "- When you have enough understanding, produce the plan — do not keep investigating "
                    "indefinitely.\n\n"
                    "Output a structured plan with these sections:\n"
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
                    "You are a specialized coding agent for implementing, fixing, and modifying code. "
                    "Your job is to get work done by using tools.\n\n"
                    "RULES:\n"
                    "- You MUST use tools (write_file, edit_file, read_file, etc.) to accomplish tasks.\n"
                    "- Talking about what needs to be done is NOT enough — you must actually call the tools.\n"
                    "- Once you have enough information, execute immediately. Do not describe what you intend to "
                    "do and then stop — follow through and complete it.\n"
                    "- Keep your text commentary brief. The real work happens through tool calls.\n\n"
                    "Good:\n"
                    "  \"I'll add the function now.\" → calls edit_file immediately\n"
                    "Bad:\n"
                    "  \"I need to add the function...\" → no tool call, just talking\n\n"
                    "You can read, write, and edit files, run shell commands, execute Python code, "
                    "search the web, and track tasks with todos."
                )

        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.doom_loop_threshold = doom_loop_threshold
        self.verbose = verbose
        self.chat_history: list[BaseMessage] = []
        self.last_plan = ""
        self.llm = llm

    def _filter_tools(self, tools: list[BaseTool]) -> list[BaseTool]:
        """Filter tools based on permissions."""
        return [t for t in tools if self.permissions.can_use(t.name)]

    def _build_messages(self, user_input: str, messages: list = None) -> list:
        if messages:
            return messages
        msgs = [SystemMessage(content=self.system_prompt)]
        msgs.extend(self.chat_history)
        msgs.append(HumanMessage(content=user_input))
        return msgs

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
        tool_history = []  # track last N (name, str(args)) for doom-loop detection

        turn_messages = [HumanMessage(content=user_input)]
        empty_retries = 0
        MAX_EMPTY_RETRIES = 2

        while step < self.max_iterations:
            try:
                result = self.llm.invoke(input_messages)
            except Exception as e:
                err = f"LLM call failed: {e}"
                turn_messages.append(AIMessage(content=err))
                if on_event:
                    on_event({"type": "response", "content": err})
                break

            tool_calls = []
            if hasattr(result, "tool_calls") and result.tool_calls:
                tool_calls = result.tool_calls

            if not tool_calls:
                response = result.content if hasattr(result, "content") else str(result)
                if not response and empty_retries < MAX_EMPTY_RETRIES:
                    empty_retries += 1
                    finish_reason = ""
                    if hasattr(result, "response_metadata"):
                        finish_reason = result.response_metadata.get("finish_reason", "")
                    self.logger.log_message(f"Empty LLM response (finish_reason={finish_reason}), retry {empty_retries}/{MAX_EMPTY_RETRIES}")
                    input_messages.append(SystemMessage(
                        content="The previous model call returned an empty response. "
                                "Please respond to the user's request now."
                    ))
                    continue
                turn_messages.append(AIMessage(content=response))
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

                ai_msg = AIMessage(content="", tool_calls=[tc])
                tool_msg = ToolMessage(
                    content=str(tool_output)[:100000], tool_call_id=tc_id
                )
                input_messages.append(ai_msg)
                input_messages.append(tool_msg)
                turn_messages.append(ai_msg)
                turn_messages.append(tool_msg)

                # Track tool call for doom-loop detection
                tool_history.append((name, str(args)))
                if len(tool_history) > 10:
                    tool_history.pop(0)

            step += 1

            # --- Doom-loop detection ------------------------------------------------
            if len(tool_history) >= self.doom_loop_threshold:
                last = tool_history[-1]
                count = sum(1 for h in tool_history if h == last)
                if count >= self.doom_loop_threshold:
                    force_msg = (
                        "You appear to be stuck repeating the same tool call. "
                        "Stop using tools and respond with a summary."
                    )
                    input_messages.append(SystemMessage(content=force_msg))
                    try:
                        final = self.llm.invoke(input_messages)
                        response = final.content if hasattr(final, "content") else str(final)
                    except Exception:
                        response = "I apologize, I was stuck in a loop. Please rephrase your request."
                    turn_messages.append(AIMessage(content=response))
                    if on_event:
                        on_event({"type": "thinking", "content": "[Auto-detected: repeated tool call]"})
                        on_event({"type": "response", "content": response})
                    if messages is None:
                        self.chat_history.extend(turn_messages)
                    return

        # --- Max iterations reached -- force a summary -------------------------------
        if step >= self.max_iterations:
            force_msg = (
                f"You have reached the maximum number of tool calls ({self.max_iterations}). "
                "Provide a brief summary of what you've done so far and what you recommend next. "
                "Do NOT use any tools."
            )
            input_messages.append(SystemMessage(content=force_msg))
            try:
                final = self.llm.invoke(input_messages)
                response = final.content if hasattr(final, "content") else str(final)
            except Exception:
                response = "I reached the iteration limit. Please rephrase or narrow your request."
            turn_messages.append(AIMessage(content=response))
            if on_event:
                on_event({"type": "thinking", "content": f"[Max iterations ({self.max_iterations}) reached]"})
                on_event({"type": "response", "content": response})

        if messages is None:
            self.chat_history.extend(turn_messages)

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
