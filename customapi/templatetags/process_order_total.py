from django import template
from django.conf import settings
register = template.Library()


@register.filter
def process_order_total(order):
    tax_value = float(order.total_incl_tax) * float(settings.TAX)
    tax_value = round(tax_value, 2)
    order_total = float(order.total_excl_tax) + float(order.shipping_excl_tax) + tax_value
    return order_total
