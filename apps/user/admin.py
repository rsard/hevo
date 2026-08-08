from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.user.models import User, VenueMembership

admin.site.register(User, UserAdmin)


@admin.register(VenueMembership)
class VenueMembershipAdmin(admin.ModelAdmin):
    """Admin list view for venue memberships, filterable by venue and role."""

    list_display = ('user', 'venue', 'role', 'is_active')
    list_filter = ('venue', 'role')
