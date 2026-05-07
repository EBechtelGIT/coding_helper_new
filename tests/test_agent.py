"""Tests for the agent module."""

from coding_agent.agent import CodingAgent
from coding_agent.llm import MockLLM
from coding_agent.tools import get_all_tools


def test_agent_initialization():
    llm = MockLLM(responses=["Hello!"])
    tools = get_all_tools()
    agent = CodingAgent(llm=llm, tools=tools)
    assert agent.agent is not None
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
