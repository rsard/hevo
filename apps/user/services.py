def get_active_venue(user):
    membership = user.venue_memberships.filter(is_active=True).select_related('venue').first()
    return membership.venue if membership else None
