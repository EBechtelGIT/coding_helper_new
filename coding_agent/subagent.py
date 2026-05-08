"""Subagent spawning and @mention handling."""

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from coding_agent.config import AgentConfig
from coding_agent.permissions import Permissions


@dataclass
class SubagentResult:
    id: str
    agent_name: str
    result: str = ""
    tool_calls: list = field(default_factory=list)
    success: bool = True
    error: str = ""
    started_at: float = 0
    finished_at: float = 0


class SubagentRunner:
    """Manages spawning and execution of subagents."""

    def __init__(self):
        self._results: list[SubagentResult] = []
        self._active: dict[str, bool] = {}
        self.parent_event_callback = None

    def parse_mentions(self, text: str) -> list[str]:
        """Extract @mentions from text.

        Returns list of agent names mentioned.
        """
        return re.findall(r"@(\w+)", text)

    def spawn(
        self,
        agent_config: AgentConfig,
        task: str,
        create_agent_fn,
        parent_session_id: str = "",
    ) -> SubagentResult:
        """Spawn a subagent synchronously.

        Args:
            agent_config: Configuration for the subagent.
            task: The task/prompt for the subagent.
            create_agent_fn: Callable(agent_config) -> CodingAgent instance.
            parent_session_id: ID of the parent session.

        Returns:
            SubagentResult with the outcome.
        """
        result_id = f"{agent_config.name}-{int(time.time())}"
        result = SubagentResult(
            id=result_id,
            agent_name=agent_config.name,
            started_at=time.time(),
        )

        try:
            agent = create_agent_fn(agent_config)

            system_msg = SystemMessage(content=agent.system_prompt) if agent.system_prompt else None

            messages = []
            if system_msg:
                messages.append(system_msg)
            messages.append(HumanMessage(content=task))

            run_result = agent.run_turn(
                user_input=task,
                messages=messages,
                parent_on_event=self.parent_event_callback,
            )

            result.result = run_result.get("response", "")
            result.tool_calls = run_result.get("tool_calls", [])
            result.finished_at = time.time()

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.finished_at = time.time()

        self._results.append(result)
        return result

    def spawn_async(
        self,
        agent_config: AgentConfig,
        task: str,
        create_agent_fn,
        parent_session_id: str = "",
        callback=None,
    ) -> str:
        """Spawn a subagent in a background thread.

        Returns the result ID for later retrieval.
        """
        result_id = f"{agent_config.name}-{int(time.time())}"
        self._active[result_id] = True

        def _run():
            result = SubagentResult(
                id=result_id,
                agent_name=agent_config.name,
                started_at=time.time(),
            )
            try:
                agent = create_agent_fn(agent_config)
                run_result = agent.run_turn(user_input=task)
                result.result = run_result.get("response", "")
                result.tool_calls = run_result.get("tool_calls", [])
                result.success = True
            except Exception as e:
                result.success = False
                result.error = str(e)
            finally:
                result.finished_at = time.time()
                self._active.pop(result_id, None)
                self._results.append(result)
                if callback:
                    callback(result)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return result_id

    def get_result(self, result_id: str) -> Optional[SubagentResult]:
        for r in self._results:
            if r.id == result_id:
                return r
        return None

    def is_active(self, result_id: str) -> bool:
        return self._active.get(result_id, False)

    def get_all_results(self) -> list[SubagentResult]:
        return list(self._results)
