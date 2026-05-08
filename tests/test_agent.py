"""Tests for the agent module."""

import copy

from coding_agent.agent import CodingAgent
from coding_agent.llm import MockLLM
from coding_agent.tools import get_all_tools


class ToolCallMockLLM:
    """A mock LLM that returns predefined tool calls for testing."""

    def __init__(self, tool_call_responses, final_response="Done."):
        self._tool_call_responses = list(tool_call_responses)
        self._final_response = final_response
        self.call_count = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessage

        if self.call_count < len(self._tool_call_responses):
            response = self._tool_call_responses[self.call_count]
            self.call_count += 1
            return response
        else:
            self.call_count += 1
            return AIMessage(content=self._final_response)


def test_agent_initialization():
    llm = MockLLM(responses=["Hello!"])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    assert agent.llm is not None
    assert agent.tool_map is not None
    assert len(agent.chat_history) == 0


def test_agent_run_turn():
    llm = MockLLM(responses=["Hello! I'm here to help."])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    result = agent.run_turn("Hello!")
    assert isinstance(result, dict)
    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0


def test_agent_clear_history():
    llm = MockLLM(responses=["Hello!", "How can I help?"])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    agent.run_turn("Hello!")
    assert len(agent.chat_history) > 0
    agent.clear_history()
    assert len(agent.chat_history) == 0


def test_agent_history():
    llm = MockLLM(responses=["Hello!", "I can help with that."])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    agent.run_turn("Hello!")
    history = agent.get_history()
    assert len(history) > 0


def test_agent_planning_mode():
    """Test that planning mode can be enabled."""
    llm = MockLLM(responses=["Here's my plan: ## Goal\nTest plan"])
    tools = get_all_tools()
    agent = CodingAgent(
        llm=llm,
        tools=tools,
        planning_mode=True,
        plan_file="test_plan.md",
    )
    assert agent.planning_mode is True
    assert agent.plan_file == "test_plan.md"


def test_agent_execution_turn():
    """Test execution turn (disables planning mode temporarily)."""
    llm = MockLLM(responses=["Executing the plan now."])
    tools = get_all_tools()
    agent = CodingAgent(
        llm=llm,
        tools=tools,
        planning_mode=True,
    )
    # Execution turn should disable planning mode temporarily
    result = agent.run_execution_turn("Execute the plan")
    assert isinstance(result, dict)
    assert "response" in result


def test_doom_loop_detection():
    """Test that repeating the same tool call 3+ times triggers doom-loop recovery."""
    from langchain_core.messages import AIMessage

    tools = get_all_tools()
    tool_map = {t.name: t for t in tools}
    read_tool = tool_map.get("read_file", next(iter(tool_map.values())))

    tc = {
        "name": read_tool.name,
        "args": {"filepath": "test.txt"},
        "id": "call_1",
    }

    repeating_msg = AIMessage(
        content="Let me check that file...",
        tool_calls=[
            {"name": read_tool.name, "args": {"filepath": "test.txt"}, "id": "call_1"},
        ],
    )

    # Need exactly 3 to trigger doom-loop (threshold=3) before hitting the final summary call
    llm = ToolCallMockLLM(
        tool_call_responses=[repeating_msg, repeating_msg, repeating_msg],
        final_response="I was stuck in a loop. Here's my summary.",
    )

    agent = CodingAgent(llm=llm, tools=tools, doom_loop_threshold=3)
    result = agent.run_turn("Read the file")
    response = result["response"].lower()
    assert "stuck" in response or "loop" in response or "summary" in response


def test_max_iterations_uses_default():
    """Test default max_iterations is 25 (not the old 10)."""
    from coding_agent.llm import MockLLM

    llm = MockLLM(responses=["Hello!"])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    assert agent.max_iterations == 25


def test_max_iterations_custom():
    """Test custom max_iterations is respected."""
    from coding_agent.llm import MockLLM

    llm = MockLLM(responses=["Hello!", "World!"])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools, max_iterations=5)
    assert agent.max_iterations == 5
