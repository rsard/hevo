from apps.ai.models import AIUsageLog
from apps.ai.providers import OpenAIProvider


def get_provider():
    return OpenAIProvider()


def log_usage(*, venue, response, conversation=None, latency_ms=None):
    return AIUsageLog.objects.create(
        venue=venue,
        conversation=conversation,
        model_name=response.model_name,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_ms=latency_ms,
    )
