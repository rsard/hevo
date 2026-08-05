from django.contrib import admin

from apps.venue.models import (
    DecorationOption,
    Document,
    EventType,
    FAQ,
    Image,
    Menu,
    MenuItem,
    OpeningHours,
    Package,
    Venue,
)


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'whatsapp_number', 'is_active')
    search_fields = ('name', 'whatsapp_number')
    inlines = [OpeningHoursInline]


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'price_per_person')
    list_filter = ('venue',)
    inlines = [MenuItemInline]


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'min_guests', 'max_guests')
    list_filter = ('venue',)


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'event_type', 'base_price')
    list_filter = ('venue',)


@admin.register(DecorationOption)
class DecorationOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'price')
    list_filter = ('venue',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'venue', 'order')
    list_filter = ('venue',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue')
    list_filter = ('venue',)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'venue', 'order')
    list_filter = ('venue',)
