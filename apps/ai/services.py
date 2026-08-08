from apps.ai.models import AIUsageLog
from apps.ai.providers import OpenAIProvider


def get_provider():
    """Returns the LLM provider instance used to generate AI replies."""
    return OpenAIProvider()


def log_usage(*, venue, response, conversation=None, latency_ms=None):
    """Records token usage and latency for an LLM call."""
    return AIUsageLog.objects.create(
        venue=venue,
        conversation=conversation,
        model_name=response.model_name,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_ms=latency_ms,
    )
