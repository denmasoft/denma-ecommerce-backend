from oscar.apps.address.models import Country
from oscarapi.basket import operations
from oscar.core.loading import get_model
from rest_framework.authtoken.models import Token
from oscarapi.utils import login_and_upgrade_session
from customapi.partner.strategy import Selector
from django.shortcuts import get_object_or_404
import serializers
from .serializers import (CategorySerializer)
from rest_framework.response import Response
from oscar.apps.catalogue.models import Product
from customapi.products.serializers import (ProductLinkSerializer, ProductSerializer, ProductImageSerializer,
                                            PriceTaxSerializer, OptionsSerializer, ProdSerializer)
from django.conf import settings
Basket = get_model('basket', 'Basket')
Category = get_model('catalogue', 'Category')
ProductCategory = get_model('catalogue', 'ProductCategory')

__all__ = (
    'process_hair_colors',
    'process_images',
    'process_products',
    'process_tree',
    'process_leafs',
    'process_variants',
    'process_ancestor',
    'process_parent',
    'fetch_ancestors',
    'process_category_products',
    'fetch_ancestors_and_self'
)


def process_ancestor(ancestor, request):
    return ancestor.name


def process_parent(parent, request):
    name = ''
    if parent is not None:
        ser = CategorySerializer(parent, context={'request': request})
        name = ser.data['name']
    return name


def process_hair_colors(category, request):
    ancestors = category.get_ancestors()
    for ancestor in ancestors:
        name = process_ancestor(ancestor, request)
        if name in "Hair Color":
            return True
    return False


def fetch_ancestors(category, request):
    ancestors = category.get_ancestors()
    result = []
    for ancestor in ancestors:
        result.append({
            "name": ancestor.name,
            "id": ancestor.id,
        })
    return result


def fetch_ancestors_and_self(category, request):
    ancestors = category.get_ancestors_and_self()
    result = []
    for ancestor in ancestors:
        result.append({
            "name": ancestor.name,
            "id": ancestor.id,
        })
    return result


def process_images(images, request):
    result = []
    for image in images:
        ser = ProductImageSerializer(image, context={'request': request})
        result.append({
            "pos": ser.data['display_order'],
            "image": ser.data['original'],
        })
    return result


def process_products(category, request):
    result = []
    offset = 0
    limit = 12
    if 'offset' in request.data:
        offset = request.data['offset']
    if 'limit' in request.data:
        limit = request.data['limit']
    products = Product.objects.filter(categories__id=category.id)[offset:limit]
    for product in products:
        ser = ProdSerializer(product, context={'request': request})
        categories = ser.data['categories']
        prodcat = categories[0]
        prodcat = get_object_or_404(Category, pk=prodcat)
        partner_sku = ''
        price_retail = ser.data['price']['incl_tax']
        if product.stockrecords.count() > 0:
            stockrecord = product.stockrecords.first()
            partner_sku = stockrecord.partner_sku
            price_retail = stockrecord.cost_price
        result.append({'url': ser.data['url'],
                       'id': ser.data['id'],
                       'title': ser.data['title'], 'description': ser.data['description'],
                       'reviews': ser.data['reviews'],
                       'date_created': ser.data['date_created'], 'date_updated': ser.data['date_updated'],
                       'attributes': ser.data['attributes'], 'categories': ser.data['categories'],
                       'product_class': ser.data['product_class'], 'rating': ser.data['rating'],
                       'partner_sku': partner_sku, 'images': ser.data['images'],
                       'price': ser.data['price'], 'price_retail': price_retail, 'availability': ser.data['availability'],
                       'options': ser.data['options'],
                       'ancestors': fetch_ancestors_and_self(prodcat, request), 'recommended': ser.data['recommended_products']})
    return result


def process_category_products(products, request):
    result = []
    for product in products:
        ser = ProdSerializer(product, context={'request': request})
        categories = ser.data['categories']
        prodcat = categories[0]
        prodcat = get_object_or_404(Category, pk=prodcat)
        partner_sku = ''
        price_retail = ser.data['price']['incl_tax']
        if product.stockrecords.count() > 0:
            stockrecord = product.stockrecords.first()
            partner_sku = stockrecord.partner_sku
            price_retail = stockrecord.cost_price
        result.append({'url': ser.data['url'],
                       'id': ser.data['id'],
                       'title': ser.data['title'], 'description': ser.data['description'],
                       'reviews': ser.data['reviews'],
                       'date_created': ser.data['date_created'], 'date_updated': ser.data['date_updated'],
                       'attributes': ser.data['attributes'], 'categories': ser.data['categories'],
                       'product_class': ser.data['product_class'], 'rating': ser.data['rating'],
                       'partner_sku': partner_sku, 'images': ser.data['images'],
                       'price': ser.data['price'], 'price_retail': price_retail, 'availability': ser.data['availability'],
                       'options': ser.data['options'],
                       'ancestors': fetch_ancestors_and_self(prodcat, request), 'recommended': ser.data['recommended_products']})
    return result


def count_process_products(category, request):
    products = Product.objects.filter(categories__id=category.id).count()
    return products


def process_tree(categories, request):
    result = []
    for category in categories:
        ser = CategorySerializer(category, context={'request': request})
        products = 0
        if category.name == 'Hair Color':
            products = category.get_children_count()
            products += count_process_variants(category.get_descendants(), request)
        elif process_hair_colors(category, request):
            products = category.get_children_count()
            products += count_process_variants(category.get_descendants(), request)
        else:
            products = ProductCategory.objects.filter(category=category).count()
        result.append({
            "name": ser.data['name'],
            "id": ser.data['id'],
            "description": ser.data['description'],
            "image": ser.data['image'],
            "products": products,
            "ancestors": fetch_ancestors(category, request)
        })
    return result


def process_leafs(categories, request):
    result = []
    for category in categories:
        if category.is_leaf():
            ser = CategorySerializer(category, context={'request': request})
            # products = ProductCategory.objects.filter(category=category).count()
            result.append({
                "name": ser.data['name'],
                "id": ser.data['id'],
                "description": ser.data['description'],
                "image": ser.data['image'],
                "hair_color": True,
                "ancestors": fetch_ancestors(category, request)
            })
        else:
            process_leafs(category.get_descendants(), request)

    return result


def process_variants(categories, request):
    result = []
    for category in categories:
        if category.is_leaf():
            # ser = CategorySerializer(category, context={'request': request})
            # products = ProductCategory.objects.filter(category=category).count()
            products = process_products(category, request)
            for prod in products:
                result.append(prod)
        else:
            process_leafs(category.get_descendants(), request)

    return result


def count_process_variants(categories, request):
    result = 0
    for category in categories:
        if category.is_leaf():
            result += count_process_products(category, request)

    return result


def process_category_list(categories, request):
    result = []
    for category in categories:
        hair_color = process_hair_colors(category, request)
        ser = CategorySerializer(category, context={'request': request})
        products = ProductCategory.objects.filter(category=category).count()
        result.append({
            "children": process_category_list(category.get_children(), request),
            "name": ser.data['name'],
            "id": ser.data['id'],
            "description": ser.data['description'],
            "image": ser.data['image'],
            "products": products,
            'hair_color': hair_color,
            "ancestors": fetch_ancestors(category, request)
        })
    return result
