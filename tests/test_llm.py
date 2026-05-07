"""Tests for the LLM module."""

from coding_agent.llm import MockLLM


def test_mock_llm_init_empty():
    mock = MockLLM()
    assert len(mock.responses) == 0


def test_mock_llm_init_with_responses():
    mock = MockLLM(responses=["resp1", "resp2"])
    assert len(mock.responses) == 2


def test_mock_llm_returns_predefined_responses():
    mock = MockLLM(responses=["hello", "world"])
    response1 = mock.invoke("test")
    response2 = mock.invoke("test")
    assert "hello" in response1.content.lower() or response1.content == "hello"
    assert "world" in response2.content.lower() or response2.content == "world"


def test_mock_llm_add_response():
    mock = MockLLM()
    assert len(mock.responses) == 0
    mock.responses.append("new response")
    assert len(mock.responses) == 1
