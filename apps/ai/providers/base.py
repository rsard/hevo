from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Structured result of a single LLM completion call."""

    content: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int


class LLMProvider(ABC):
    """Common interface all LLM providers must implement."""

    @abstractmethod
    def generate(self, *, system_prompt, messages, temperature=0.7):
        """messages is a list of {"role": "user"|"assistant", "content": str} dicts."""
