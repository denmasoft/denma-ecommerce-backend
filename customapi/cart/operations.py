from oscar.apps.address.models import Country
from oscarapi.basket import operations
from oscar.core.loading import get_model
from rest_framework.authtoken.models import Token
from oscarapi.utils import login_and_upgrade_session
from customapi.partner.strategy import Selector
from django.shortcuts import get_object_or_404
from customapi.products.serializers import (PriceTaxSerializer)
from customapi.cart.serializers import (CustomBasketSerializer)
from customapi.user.models import WholeSale
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
Product = get_model('catalogue', 'Product')
Basket = get_model('basket', 'Basket')
import requests
__all__ = (
    'getitems',
    'getdiscounts',
    'getShipping',
    'get_basket'
)

session = requests.Session()

def getitems(order):
    """ """
    items = []
    currency = "USD"
    for line in order.lines.all():
        if line.product.stockrecords.count() > 0:
            stockrecord = line.product.stockrecords.first()
            sku = stockrecord.partner_sku
            price_cost = stockrecord.cost_price                
        currency = order.currency
        quantity = line.quantity
        strategy = Selector().strategy()
        product = get_object_or_404(Product, pk=line.product.id)
        ser = PriceTaxSerializer(
            strategy.fetch_for_product(product).price,
            context={'request': None})
        price = ser.data
        price = price['incl_tax']
        if order.user is not None:
            try:
                wholesale = WholeSale.objects.get(user=order.user)
                if wholesale:
                    price = price_cost
            except ObjectDoesNotExist:
                ''
        items.append({
            "name": str(line.product.title),
            "sku": str(sku),
            "price": price,
            "currency": str(currency),
            "quantity": int(quantity),
        })
    return items


def order_total(order):
    """ """
    total = float(0.00)
    for line in order.lines.all():
        if line.product.stockrecords.count() > 0:
            stockrecord = line.product.stockrecords.first()
            sku = stockrecord.partner_sku
            price_cost = stockrecord.cost_price                
        quantity = line.quantity
        sum = quantity * price_cost
        total+=float(sum)
    return total


def getShipping(order):
    items = []
    if order.shipping_code:
        items.append({
            "name": str(order.shipping_method),
            "price": float(order.shipping_incl_tax),
            "currency": 'USD',
            "quantity": 1,
        })
    return items


def getShippingAddress(shipping_address):
    item = {'first_name': shipping_address.first_name,
              'last_name': shipping_address.last_name,
              'address': shipping_address.line1,
              'city': shipping_address.line4,
              'state': shipping_address.state, 'postcode': shipping_address.postcode}
    return item

def getdiscounts(order):
    """ """
    items = []
    currency = "USD"

    for offer in order.discounts.all():
        items.append({
            "name": str(offer.offer_name),
            "price": str(-offer.amount),
            "currency": str(currency),
            "quantity": 1,
        })
    return items


def get_basket(token, request):
    data = {
        "token": token,
    }
    resp = session.get(settings.API_URL + '/basket/')
    basket_data = resp.json()
    return basket_data['id']
