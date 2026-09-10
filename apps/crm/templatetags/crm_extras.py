import re

from django import template

register = template.Library()

URGENCY_COLORS = {
    "low": "success",
    "medium": "warning",
    "high": "warning",
    "urgent": "danger",
}

STAGE_COLORS = {
    "new": "secondary",
    "contacted": "secondary",
    "qualified": "primary",
    "negotiation": "warning",
    "won": "success",
    "lost": "danger",
}

LABEL_COLORS = {
    "blue": "primary",
    "green": "success",
    "magenta": "danger",
    "yellow": "warning",
    "aqua": "info",
    "orange": "warning",
    "violet": "primary",
    "red": "danger",
}


@register.filter
def urgency_color(urgency):
    """Bootstrap contextual color name for a Lead.Urgency value."""
    return URGENCY_COLORS.get(urgency, "secondary")


@register.filter
def stage_color(stage):
    """Bootstrap contextual color name for a Lead.Stage value."""
    return STAGE_COLORS.get(stage, "secondary")


@register.filter
def label_color(color):
    """Bootstrap contextual color name for a Label.Color value."""
    return LABEL_COLORS.get(color, "secondary")


@register.filter
def collapse_blank_lines(text):
    """Collapses runs of 2+ newlines into one. AI-generated messages often
    have blank-line paragraph breaks that, combined with the chat bubble's
    white-space: pre-wrap, render as an oversized gap inside the message."""
    if not text:
        return text
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{2,}", "\n", normalized)
