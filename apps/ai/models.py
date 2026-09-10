from django.db import models

from apps.core.models import TenantModel


class AIUsageLog(TenantModel):
    """Tracks token usage and latency for a single LLM call, for cost monitoring."""

    conversation = models.ForeignKey(
        "conversation.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_usage_logs",
    )
    provider = models.CharField(max_length=50, default="openai")
    model_name = models.CharField(max_length=100)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.model_name} - {self.venue}"
