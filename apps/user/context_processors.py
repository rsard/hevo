from apps.user.services import get_active_venue


def active_venue(request):
    """Expose the logged-in user's active venue, and its active lead count for
    the sidebar summary, to every template."""
    if not request.user.is_authenticated:
        return {'active_venue': None, 'active_venue_lead_count': None}

    venue = get_active_venue(request.user)
    lead_count = None
    if venue is not None:
        from apps.crm.models import Lead

        lead_count = (
            Lead.objects.filter(venue=venue)
            .exclude(stage__in=[Lead.Stage.WON, Lead.Stage.LOST])
            .count()
        )

    return {'active_venue': venue, 'active_venue_lead_count': lead_count}
