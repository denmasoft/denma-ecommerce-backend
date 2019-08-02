import collections

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


__all__ = ('api_root',)


def PUBLIC_APIS(r, f):
    return [
        ('reset-password', reverse('reset-password', request=r, format=f)),
        ('load-products', reverse('load-products', request=r, format=f)),
        ('get-slugs', reverse('get-slugs', request=r, format=f)),
        ('find-products', reverse('find-products', request=r, format=f)),
        ('reset-orders', reverse('reset-orders', request=r, format=f)),
        ('encrypt-card', reverse('decrypt-card', request=r, format=f)),
        ('decrypt-card', reverse('decrypt-card', request=r, format=f)),
        ('test-email', reverse('test-email', request=r, format=f)),
        ('api-customer-contact', reverse('api-customer-contact', request=r, format=f)),
        ('facebook-login', reverse('facebook-login', request=r, format=f)),
        ('facebook-callback', reverse('facebook-callback', request=r, format=f)),
        ('google-login', reverse('google-login', request=r, format=f)),
        ('google-callback', reverse('google-callback', request=r, format=f)),
        ('wholesale-license', reverse('wholesale-license', request=r, format=f)),
        ('customer-register', reverse('user-register', request=r, format=f)),
        ('recover-password', reverse('recover-password', request=r, format=f)),
        ('customer-profile', reverse('customer-profile', request=r, format=f)),
        ('customer-orders', reverse('customer-orders', kwargs={'pk': 1}, request=r, format=f)),
        ('remove-address', reverse('remove-address', request=r, format=f)),
        ('review-product', reverse('review-product', request=r, format=f)),
        ('api-login', reverse('api-login', request=r, format=f)),
        ('newsletter-subscribe', reverse('newsletter-subscribe', request=r, format=f)),
        ('customer-logout', reverse('customer-logout', request=r, format=f)),
        ('paypal-payment', reverse('paypal-payment', kwargs={'pk': 1}, request=r, format=f)),
        ('stripe-payment', reverse('stripe-payment', kwargs={'pk': 1}, request=r, format=f)),
        ('paypal-execute', reverse('paypal-execute', kwargs={'pk': 1}, request=r, format=f)),
        ('stripe-execute', reverse('stripe-execute', kwargs={'pk': 1}, request=r, format=f)),
        ('api-cart-add-product', reverse('api-cart-add-product', request=r, format=f)),
        ('api-cart-shipping-rates', reverse('api-cart-shipping-rates', request=r, format=f)),
        ('api-cart-checkout', reverse('api-cart-checkout', request=r, format=f)),
        ('api-cart-remove-product', reverse('api-cart-remove-product', request=r, format=f)),
        ('basket-lines-list', reverse('basket-lines-list', kwargs={'pk': 1}, request=r, format=f)),
        ('api-token-auth', reverse('api-token-auth', request=r, format=f)),
        ('login', reverse('api-login', request=r, format=f)),
        ('basket', reverse('api-basket', request=r, format=f)),
        ('basket-add-product', reverse('api-basket-add-product', request=r, format=f)),
        ('checkout', reverse('api-checkout', request=r, format=f)),

        ('categories', reverse('category-list', request=r, format=f)),
        ('categories-children', reverse('category-children', kwargs={'pk': 1}, request=r, format=f)),
	    ('categories-by', reverse('category-by', kwargs={'pk': 1}, request=r, format=f)),
        ('products', reverse('product-list', request=r, format=f)),
        ('products-detail', reverse('products-detail', kwargs={'pk': 1}, request=r, format=f)),
        ('products-by-category', reverse('products-by-category', kwargs={'pk': 1}, request=r, format=f)),
        ('products-by-search', reverse('products-by-search', kwargs={'pattern':'search terms'}, request=r, format=f)),

        ('countries', reverse('country-list', request=r, format=f)),
        ('paymenttypes', reverse('sourcetype-list', request=r, format=f)),

        ('api-basket', reverse('api-basket', request=r, format=f)),
        ('basket-detail', reverse('basket-detail', kwargs={'pk': 1}, request=r, format=f)),
        ('wishlist', reverse('api-wishlist', request=r, format=f)),
        ('wishlist-detail', reverse('wishlist-detail', kwargs={'pk': 1}, request=r, format=f)),
        ('wishlist-add-product', reverse('wishlist-add-product', kwargs={'pk': 1}, request=r, format=f)),
        ('wishlist-add-prod', reverse('wishlist-add-prod', request=r, format=f)),
        ('wishlist-remove-product', reverse('wishlist-remove-product', kwargs={'pk': 1}, request=r, format=f)),
        ('wishlist-remove-prod', reverse('wishlist-remove-prod', request=r, format=f)),
        ('wishlist-add-to-basket', reverse('api-wishlist-add-to-basket', request=r, format=f)),

    ]


def PROTECTED_APIS(r, f):
    return [
        ('baskets', reverse('basket-list', request=r, format=f)),
        ('lines', reverse('line-list', request=r, format=f)),
        ('lineattributes', reverse('lineattribute-list', request=r, format=f)),
        ('options', reverse('option-list', request=r, format=f)),
        ('stockrecords', reverse('stockrecord-list', request=r, format=f)),
        ('users', reverse('user-list', request=r, format=f)),
    ]


@api_view(('GET',))
def api_root(request, format=None):
    """
    GET:
    Display all available urls.

    Since some urls have specific permissions, you might not be able to access
    them all.
    """
    apis = PUBLIC_APIS(request, format)
    if request.user.is_staff:
        apis += PROTECTED_APIS(request, format)

    return Response(collections.OrderedDict(apis))
