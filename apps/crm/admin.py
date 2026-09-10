from django.contrib import admin

from apps.crm.models import CalendarConnection, Label, Lead, LeadActivity, Visit


class LeadActivityInline(admin.TabularInline):
    """Inline editor for a lead's activity log entries within the Lead admin page."""

    model = LeadActivity
    extra = 0


class VisitInline(admin.TabularInline):
    """Inline editor for a lead's visits within the Lead admin page."""

    model = Visit
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """Admin configuration for Lead: list/filter columns and inline activities/visits."""

    list_display = (
        "customer_name", "customer_phone", "venue", "stage", "qualification_score", "assigned_to",
        "escalated_at",
    )
    list_filter = ("venue", "stage", "sentiment")
    search_fields = ("customer_name", "customer_phone")
    filter_horizontal = ("labels",)
    inlines = [LeadActivityInline, VisitInline]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    """Admin configuration for Label: list and filter columns."""

    list_display = ("name", "venue", "color")
    list_filter = ("venue", "color")


@admin.register(CalendarConnection)
class CalendarConnectionAdmin(admin.ModelAdmin):
    """Admin configuration for CalendarConnection: list columns."""

    list_display = ("venue", "provider", "calendar_id")
