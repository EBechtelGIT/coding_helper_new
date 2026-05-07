"""Logging utilities for the Coding Agent."""

import sys
from typing import Optional

from langchain_core.messages import BaseMessage


class AgentLogger:
    """Logger for agent operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log_turn_start(self, user_input: str) -> None:
        if self.verbose:
            truncated = user_input[:100] + ("..." if len(user_input) > 100 else "")
            print(f"[Turn] User: {truncated}", file=sys.stderr)

    def log_model_call(self, message_count: int) -> None:
        if self.verbose:
            print(f"[LLM] Calling model with {message_count} messages", file=sys.stderr)

    def log_model_response(self, response: BaseMessage) -> None:
        if self.verbose:
            content = getattr(response, 'content', str(response))
            if isinstance(content, list):
                content = str(content)
            truncated = content[:200] + ("..." if len(content) > 200 else "")
            print(f"[LLM] Response: {truncated}", file=sys.stderr)

    def log_tool_call(self, name: str, params: dict) -> None:
        if self.verbose:
            params_str = str(params)[:100] + ("..." if len(str(params)) > 100 else "")
            print(f"[Tool] Calling: {name} | Params: {params_str}", file=sys.stderr)

    def log_tool_result(self, name: str, result: str, success: bool) -> None:
        if self.verbose:
            truncated = result[:150] + ("..." if len(result) > 150 else "")
            status = "ok" if success else "ERR"
            print(f"[Tool] {status} {name}: {truncated}", file=sys.stderr)

    def log_token_usage(self, usage_metadata: Optional[dict]) -> None:
        if self.verbose and usage_metadata:
            input_tokens = usage_metadata.get('input_tokens', 0)
            output_tokens = usage_metadata.get('output_tokens', 0)
            total = input_tokens + output_tokens
            print(f"[Tokens] In: {input_tokens} | Out: {output_tokens} | Total: {total}", file=sys.stderr)

    def log_plan_generated(self, plan_path: str) -> None:
        if self.verbose:
            print(f"[Plan] Generated: {plan_path}", file=sys.stderr)

    def log_session(self, action: str, session_id: str = "") -> None:
        if self.verbose:
            print(f"[Session] {action}: {session_id}", file=sys.stderr)

    def log_compaction(self, old_count: int, new_count: int) -> None:
        if self.verbose:
            print(f"[Compact] Reduced messages: {old_count} -> {new_count}", file=sys.stderr)

    def log_subagent(self, name: str, task: str) -> None:
        if self.verbose:
            print(f"[Subagent] Spawning {name}: {task[:80]}", file=sys.stderr)

    def log_permission(self, tool: str, action: str) -> None:
        if self.verbose:
            print(f"[Permission] {tool}: {action}", file=sys.stderr)

    def log_separator(self) -> None:
        if self.verbose:
            print("-" * 50, file=sys.stderr)

    def log_message(self, message: str) -> None:
        if self.verbose:
            print(f"[Info] {message}", file=sys.stderr)
