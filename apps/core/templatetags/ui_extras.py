from django import template

register = template.Library()

# Bootstrap's contextual colors, used as a fixed deterministic palette for
# avatars, kanban accents, and calendar events instead of hand-rolled CSS.
BOOTSTRAP_COLORS = ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'dark']


@register.filter
def initials(name):
    """First two letters of a single name, or first+last initial for a full name."""
    if not name:
        return '?'
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def avatar_color(user_id):
    """Deterministic Bootstrap color name for a user id so their avatar color is stable."""
    if user_id is None:
        return BOOTSTRAP_COLORS[0]
    return BOOTSTRAP_COLORS[user_id % len(BOOTSTRAP_COLORS)]


@register.filter
def color_index(value, count=None):
    """Deterministic Bootstrap color name for a string identifier (e.g. an external
    event id) so the same item always gets the same color across requests."""
    if not value:
        return BOOTSTRAP_COLORS[0]
    palette = BOOTSTRAP_COLORS[:count] if count else BOOTSTRAP_COLORS
    return palette[sum(ord(c) for c in str(value)) % len(palette)]
