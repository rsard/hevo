from django.contrib import admin

from apps.backoffice.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('venue', 'plan_name', 'monthly_price', 'status', 'started_at')
    list_filter = ('status',)
