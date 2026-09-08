from django.contrib import admin

from apps.venue.models import (
    DecorationOption,
    EventType,
    FAQ,
    Menu,
    MenuItem,
    OpeningHours,
    Package,
    Venue,
)


class OpeningHoursInline(admin.TabularInline):
    """Inline editor for a venue's weekly opening hours, shown on the Venue admin page."""

    model = OpeningHours
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    """Admin for Venue records, listing name, WhatsApp number and active status."""

    list_display = ('name', 'whatsapp_number', 'is_active')
    search_fields = ('name', 'whatsapp_number')
    inlines = [OpeningHoursInline]


class MenuItemInline(admin.TabularInline):
    """Inline editor for a menu's items, shown on the Menu admin page."""

    model = MenuItem
    extra = 0


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin for Menu records, filterable by venue."""

    list_display = ('name', 'venue', 'price_per_person')
    list_filter = ('venue',)
    inlines = [MenuItemInline]


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    """Admin for EventType records, filterable by venue."""

    list_display = ('name', 'venue', 'min_guests', 'max_guests')
    list_filter = ('venue',)


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    """Admin for Package records, filterable by venue."""

    list_display = ('name', 'venue', 'event_type', 'base_price')
    list_filter = ('venue',)


@admin.register(DecorationOption)
class DecorationOptionAdmin(admin.ModelAdmin):
    """Admin for DecorationOption records, filterable by venue."""

    list_display = ('name', 'venue', 'price')
    list_filter = ('venue',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """Admin for FAQ records, filterable by venue."""

    list_display = ('question', 'venue', 'order')
    list_filter = ('venue',)
