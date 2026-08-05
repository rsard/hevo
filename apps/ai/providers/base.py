from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, *, system_prompt, messages, temperature=0.7):
        """messages is a list of {"role": "user"|"assistant", "content": str} dicts."""
