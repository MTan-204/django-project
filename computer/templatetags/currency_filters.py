from decimal import Decimal
from django import template

register = template.Library()

@register.filter
def vnd(value):
    if value is None or value == '':
        return '0'

    try:
        value = Decimal(value)
    except Exception:
        return '0'

    return f"{value:,.0f}".replace(",", ".")