from django.utils.numberformat import format as django_number_format


def format_currency(value):
    """Formats a number as Brazilian currency: R$ 17.500,00.

    For Django template output, USE_THOUSAND_SEPARATOR already handles this
    automatically — this is for the places that build a string in plain
    Python (WhatsApp message bodies, model __str__, AI prompt context)."""
    if value is None:
        return ""
    formatted = django_number_format(value, decimal_pos=2, decimal_sep=",", grouping=3, thousand_sep=".")
    return f"R$ {formatted}"
