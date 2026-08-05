from django.contrib import admin

from apps.ai.models import AIUsageLog


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ('venue', 'model_name', 'prompt_tokens', 'completion_tokens', 'created_at')
    list_filter = ('venue', 'model_name')
