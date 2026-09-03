import abc
from typing import Any, List, Dict

class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers to decouple Gemini from the Orchestrator."""

    @abc.abstractmethod
    def bind_tools(self, tools: List[Any]) -> None:
        """Bind a list of tools (functions or schemas) to the LLM."""
        pass

    @abc.abstractmethod
    def invoke(self, messages: List[Any]) -> Any:
        """Invoke the LLM with a list of messages. Returns the LLM response (can include tool calls)."""
        pass


class GeminiProvider(LLMProvider):
    """Implementation of LLMProvider for Google Gemini using LangChain."""

    def __init__(self, model_name: str, api_key: str, temperature: float = 0.0):
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            api_key=api_key,
            temperature=temperature
        )
        self.llm_with_tools = self.llm

    def bind_tools(self, tools: List[Any]) -> None:
        """Bind LangChain tools to the Gemini model."""
        self.llm_with_tools = self.llm.bind_tools(tools)

    def invoke(self, messages: List[Any]) -> Any:
        """Invoke Gemini. Expected to return a LangChain AIMessage with potential tool_calls."""
        return self.llm_with_tools.invoke(messages)
