from django.conf import settings
from openai import OpenAI

from apps.ai.providers.base import LLMProvider, LLMResponse

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    """LLMProvider implementation backed by the OpenAI chat completions API."""

    def __init__(self, model_name=DEFAULT_MODEL):
        """Sets up the OpenAI client for the given model."""
        self.model_name = model_name
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(self, *, system_prompt, messages, temperature=0.7):
        """Calls the OpenAI chat completions API and returns a normalized LLMResponse."""
        response = self._client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content,
            model_name=self.model_name,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
