from apps.user.services import get_active_venue


def active_venue(request):
    if not request.user.is_authenticated:
        return {'active_venue': None}
    return {'active_venue': get_active_venue(request.user)}
