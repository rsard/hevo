from django import template

register = template.Library()

URGENCY_COLORS = {
    'low': 'success',
    'medium': 'warning',
    'high': 'warning',
    'urgent': 'danger',
}

STAGE_COLORS = {
    'new': 'secondary',
    'contacted': 'secondary',
    'qualified': 'primary',
    'negotiation': 'warning',
    'won': 'success',
    'lost': 'danger',
}

LABEL_COLORS = {
    'blue': 'primary',
    'green': 'success',
    'magenta': 'danger',
    'yellow': 'warning',
    'aqua': 'info',
    'orange': 'warning',
    'violet': 'primary',
    'red': 'danger',
}


@register.filter
def urgency_color(urgency):
    """Bootstrap contextual color name for a Lead.Urgency value."""
    return URGENCY_COLORS.get(urgency, 'secondary')


@register.filter
def stage_color(stage):
    """Bootstrap contextual color name for a Lead.Stage value."""
    return STAGE_COLORS.get(stage, 'secondary')


@register.filter
def label_color(color):
    """Bootstrap contextual color name for a Label.Color value."""
    return LABEL_COLORS.get(color, 'secondary')
