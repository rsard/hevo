def get_active_venue(user):
    """Return the venue for the user's first active membership, or None if
    they have no active membership (e.g. staff accounts without a venue)."""
    membership = user.venue_memberships.filter(is_active=True).select_related('venue').first()
    return membership.venue if membership else None
