"""LLM setup supporting multiple providers."""

import os
from typing import List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import Runnable


LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "180"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))


def create_llm(
    tools: List,
    provider: str = "azure",
    model_name: str = "",
    temperature: float = 0,
) -> BaseLanguageModel:
    """Create LLM based on provider configuration.

    Supported providers: azure, openai, anthropic
    """
    if provider == "openai":
        return _create_openai_llm(tools, model_name or "gpt-4o", temperature)
    elif provider == "anthropic":
        return _create_anthropic_llm(tools, model_name or "claude-sonnet-4-20250514", temperature)
    else:
        return _create_azure_llm(tools, model_name or "gpt-5.1", temperature)


def _create_azure_llm(tools, model_name, temperature):
    from langchain_openai import AzureChatOpenAI

    # Get endpoint from env, support multiple formats
    azure_endpoint = os.getenv("AZURE_ENDPOINT")
    if not azure_endpoint:
        # Try alternative env var names
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not azure_endpoint:
        raise ValueError("Azure endpoint not found in environment variables. Please set AZURE_ENDPOINT or AZURE_OPENAI_ENDPOINT.")

    api_version = os.getenv("AZURE_API_VERSION", "2025-03-01-preview")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")

    return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        deployment_name=model_name,
        api_key=api_key,
        temperature=temperature,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
        max_completion_tokens=LLM_MAX_TOKENS,
    ).bind_tools(tools)


def _create_openai_llm(tools, model_name, temperature):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=temperature,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
        max_tokens=LLM_MAX_TOKENS,
    ).bind_tools(tools)


def _create_anthropic_llm(tools, model_name, temperature):
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model_name,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=temperature,
        timeout=LLM_TIMEOUT,
        max_tokens=LLM_MAX_TOKENS,
    ).bind_tools(tools)


class MockLLM(Runnable):
    """A mock LLM for testing that returns predefined responses."""

    def __init__(self, responses: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.responses = list(responses) if responses else []
        self.call_count = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        if self.call_count < len(self.responses):
            response_text = self.responses[self.call_count]
            self.call_count += 1
        else:
            response_text = f"[MockLLM] No more responses. Call count: {self.call_count}"

        return AIMessage(content=response_text)

    async def ainvoke(self, input, config=None, **kwargs):
        return self.invoke(input, config, **kwargs)
