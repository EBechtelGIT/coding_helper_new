"""Placeholder middleware module for the Coding Agent.

Kept for API compatibility — the agent no longer uses middleware
decorators. The functions here are plain helpers that the agent
calls directly when needed.
"""

import sys
from typing import Any, Callable

_logger = None

_planning_mode = False
_plan_file = "PLAN.md"

_compaction_enabled = False
_compaction_max_messages = 50
_compaction_keep_messages = 20


def set_logger(logger):
    global _logger
    _logger = logger


def set_planning_mode(enabled: bool, plan_file: str = "PLAN.md"):
    global _planning_mode, _plan_file
    _planning_mode = enabled
    _plan_file = plan_file


def set_compaction(enabled: bool, max_messages: int = 50, keep_messages: int = 20):
    global _compaction_enabled, _compaction_max_messages, _compaction_keep_messages
    _compaction_enabled = enabled
    _compaction_max_messages = max_messages
    _compaction_keep_messages = keep_messages


def log_before_model(state: dict, runtime=None) -> dict[str, Any] | None:
    if _logger:
        messages = state.get("messages", [])
        _logger.log_model_call(len(messages))
    return None


def log_after_model(state: dict, runtime=None) -> dict[str, Any] | None:
    if _logger:
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            _logger.log_model_response(last_msg)
            if hasattr(last_msg, 'usage_metadata') and last_msg.usage_metadata:
                _logger.log_token_usage(last_msg.usage_metadata)
    return None


def log_tool_call(request, handler: Callable) -> Any:
    if _logger:
        tool_name = request.get("name", "unknown") if isinstance(request, dict) else "unknown"
        tool_args = request.get("args", {}) if isinstance(request, dict) else {}
        _logger.log_tool_call(tool_name, tool_args)

    result = handler(request)

    if _logger:
        tool_name = result.get("name", "unknown") if isinstance(result, dict) else "unknown"
        success = not (hasattr(result, 'status') and result.status == 'error')
        result_text = str(getattr(result, 'content', result))
        _logger.log_tool_result(tool_name, result_text, success)

    return result


_READ_ONLY_TOOLS = {'read_file', 'glob_search', 'grep_search', 'web_search'}


def planning_mode_guard(state: dict, runtime=None) -> dict[str, Any] | None:
    if not _planning_mode:
        return None

    messages = state.get("messages", [])
    if not messages:
        return None

    last_msg = messages[-1]
    if hasattr(last_msg, 'tool_calls'):
        for tc in last_msg.tool_calls:
            tool_name = tc.get('name', '')
            if tool_name not in _READ_ONLY_TOOLS:
                return {
                    "messages": messages + [{
                        "role": "assistant",
                        "content": (
                            f"PLANNING MODE: Cannot use '{tool_name}'. "
                            "Please use only read-only tools (read_file, glob_search, "
                            "grep_search, web_search) and create a structured plan."
                        )
                    }]
                }
    return None


def generate_plan_file(state: dict, runtime=None) -> dict[str, Any] | None:
    if not _planning_mode or not _plan_file:
        return None

    messages = state.get("messages", [])
    plan_content = _extract_plan_from_messages(messages)

    if plan_content:
        try:
            with open(_plan_file, 'w', encoding='utf-8') as f:
                f.write(plan_content)
            if _logger:
                _logger.log_plan_generated(_plan_file)
        except Exception as e:
            print(f"[Plan] Error writing plan file: {e}", file=sys.stderr)

    return None


def _extract_plan_from_messages(messages) -> str:
    plan_sections = []
    in_plan = False

    for msg in messages:
        if not hasattr(msg, 'content'):
            continue

        content = str(msg.content)
        has_plan_keywords = any(
            keyword in content.lower()
            for keyword in [
                'plan', 'goal', 'approach', 'step', 'current state',
                'files to modify', 'risks', 'open questions'
            ]
        )

        if has_plan_keywords or in_plan:
            in_plan = True
            plan_sections.append(content)

    if not plan_sections:
        for msg in reversed(messages):
            if hasattr(msg, 'content') and str(msg.type) == 'assistant':
                content = str(msg.content)
                if len(content) > 50:
                    return f"# Plan\n\n{content}\n"
                break
        return ""

    return "# Plan\n\n" + "\n\n---\n\n".join(plan_sections)


def get_logging_middleware():
    return [log_before_model, log_after_model, log_tool_call]


def get_planning_middleware():
    return [planning_mode_guard, generate_plan_file]
