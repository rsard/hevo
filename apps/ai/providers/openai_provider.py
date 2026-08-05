from django.conf import settings
from openai import OpenAI

from apps.ai.providers.base import LLMProvider, LLMResponse

DEFAULT_MODEL = 'gpt-4o-mini'


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name=DEFAULT_MODEL):
        self.model_name = model_name
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(self, *, system_prompt, messages, temperature=0.7):
        response = self._client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=[{'role': 'system', 'content': system_prompt}, *messages],
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content,
            model_name=self.model_name,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
