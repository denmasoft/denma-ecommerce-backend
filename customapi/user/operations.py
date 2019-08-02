from customapi.address.models import UserAddress
from customapi.user.models import Newsletter
from customapi.user.models import WholeSale
from customapi.basket.models import Basket
from oscar.apps.address.models import Country
from customapi.wishlists.models import WishList
from customapi.wishlist.serializers import (WishListSerializer)
from customapi.cart.serializers import (CustomBasketSerializer, UserOrderSerializer)
from rest_framework.response import Response
from oscarapi.basket import operations
from oscar.core.loading import get_model
from rest_framework.authtoken.models import Token
from oscarapi.utils import login_and_upgrade_session
from customapi.user.models import CreditCard
from customapi.license.models import License
import binascii, os
from Crypto.Cipher import AES
from django.conf import settings
from django.core.mail import send_mail
import base64
from mailchimp3 import MailChimp
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
import hashlib

Basket = get_model('basket', 'Basket')
Order = get_model('order', 'Order')

__all__ = (
    'base_convert',
    'convert_base',
    'convert_base2',
    'encryptCard',
    'decryptCard',
    'merge_baskets',
    'process_phone_fax',
    'customer_login',
    'customer_logout',
    'country_data',
    'customer_data',
    'customer_credit_cards',
    'process_lines',
    'customer_cart',
    'customer_wishlist',
    'process_user_mailchimp',
    'validate_license',
    'validate_usage',
    'customer_order'
)
digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base_convert(number, fromBase, toBase):
    try:
        base10 = int(number, fromBase)
    except ValueError:
        raise
    if toBase < 2 or toBase > 36:
        raise NotImplementedError
    output_value = ''
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    sign = ''
    if base10 == 0:
        return '0'
    elif base10 < 0:
        sign = '-'
        base10 = -base10
    s = ''
    while base10 != 0:
        r = base10 % toBase
        r = int(r)
        s = digits[r] + s
        base10 //= toBase
    output_value = sign + s
    return output_value


def convert_base(num, base=16):
    if num == 0:
        return "0"

    stack = []
    while num != 0:
        stack.append(digits[num % base])
        num = num / base
    return "".join(stack[::-1])


def convert_base2(num, base=16):
    stack = []
    while True:
        stack.append(digits[num % base])
        num = num / base
        if not num:
            break
    return "".join(stack[::-1])


def encryptCard(card):
    if card is None:
        return ""
    length = len(card)
    encrypted = ""
    for index in range(len(card)):
        encrypted += convert_base2((int(card[index]) + int(5)), 16)

    return encrypted


def decryptCard(encrypted):
    if encrypted is None:
        return ""
    decrypt = ""
    for index in range(len(encrypted)):
        data = encrypted[index]
        data = base_convert(data, 16, 10)
        data = str(int(data) - int(5))
        decrypt += base_convert(data, 16, 10)

    return decrypt


def merge_baskets(anonymous_basket, basket):
    "Hook to enforce rules when merging baskets."
    basket.merge(anonymous_basket)
    anonymous_basket.delete()


def process_phone_fax(phone):
    phone_number = None
    if phone is not None:
        phone_number = [{'country_code': phone.country_code,
                         'national_number': phone.national_number,
                         'extension': phone.extension,
                         'italian_leading_zero': phone.italian_leading_zero,
                         'number_of_leading_zeros': phone.number_of_leading_zeros,
                         'country_code_source': phone.country_code_source,
                         'preferred_domestic_carrier_code': phone.preferred_domestic_carrier_code}]
    return phone_number


def customer_login(request, user):
    anonymous_basket = operations.get_anonymous_basket(request)
    request.user = user
    login_and_upgrade_session(request._request, user)
    # merge anonymous basket with authenticated basket.
    basket = operations.get_user_basket(user)
    if anonymous_basket is not None:
        merge_baskets(anonymous_basket, basket)
    operations.store_basket_in_session(basket, request.session)


def customer_logout(request):
    request = request._request
    if request.user.is_anonymous():
        basket = operations.get_anonymous_basket(request)
        # if basket:
        #   operations.flush_and_delete_basket(basket)

    request.session.clear()
    request.session.delete()
    request.session = None


def country_data(cc):
    country_info = None
    if cc is not None:
        country = Country.objects.get(printable_name=cc)
        country_info = [{"iso_3166_1_a2": country.iso_3166_1_a2,
                         "iso_3166_1_a3": country.iso_3166_1_a3,
                         "iso_3166_1_numeric": country.iso_3166_1_numeric,
                         "printable_name": country.printable_name,
                         "name": country.name,
                         "display_order": country.display_order,
                         "is_shipping_country": country.is_shipping_country,
                         "url": "/api/countries/" + country.iso_3166_1_a2 + "/"}]
    return country_info


def customer_addresses(addresses):
    items = []
    for address in addresses:
        items.append({
            'id': address.pk,
            'line1': address.line1,
            'line4': address.line4,
            'state': address.state,
            'postcode': address.postcode,
            'search_text': address.search_text,
            'phone_number': process_phone_fax(address.phone_number),
            'fax': process_phone_fax(address.fax),
            'country': country_data(address.country)
        })
    return items


def customer_credit_cards(user):
    credit_cards = []
    cards = CreditCard.objects.filter(user=user.id)
    for card in cards:
        plain = decryptCard(card.card)
        credit_cards.append({'card': plain, 'holder': card.holder})

    return credit_cards


def customer_cart(user, request, prepare=True):
    if user is not None:
        basket = operations.get_user_basket(user)
    if basket is None:
        basket = Basket.objects.create()
        basket.save()
    basket = operations.prepare_basket(basket, request) if prepare else basket
    ser = CustomBasketSerializer(basket, context={'request': request})
    return ser.data


def customer_order(user, request):
    order = None
    if user is not None:
        try:
            order = Order.objects.filter(user=user).latest('id')
            ser = UserOrderSerializer(order, context={'request': request})
            return ser.data
        except ObjectDoesNotExist:
            return None
    return order


def customer_wishlist(user, request):
    try:
        wishlist, _ = WishList.objects.get_or_create(
            owner=user, visibility=WishList.PRIVATE)
    except WishList.MultipleObjectsReturned:
        wishlist = WishList.objects.filter(owner=user).latest('id')
    ser = WishListSerializer(wishlist, context={'request': request})
    return ser.data


def customer_data(user, request):
    token, created = Token.objects.get_or_create(user=user)
    addresses = user.addresses.all()
    try:
        newsletter = Newsletter.objects.get(user=user)
        subscribe = newsletter.subscribe
    except ObjectDoesNotExist:
        subscribe = False
    license = None
    try:
        wholesale = WholeSale.objects.get(user=user)
        license = wholesale.license
    except ObjectDoesNotExist:
        license = None
    userdata = {'username': user.username,
                'id': user.id,
                'date_joined': user.date_joined,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'token': token.key,
                'addresses': customer_addresses(addresses),
                'newsletter_subscribe': subscribe,
                'wholesale_license': license,
                'credit_cards': customer_credit_cards(user),
                'wishlist': customer_wishlist(user, request),
                'cart': customer_cart(user, request),
                'order': customer_order(user, request)
                }
    return userdata


def process_user_mailchimp(user, action):
    client = MailChimp(settings.MAILCHIMP_USER, settings.MAILCHIMP_KEY)
    obj = client.lists.all(get_all=True, fields="lists.name,lists.id")
    lists = obj['lists']
    for mlist in lists:
        if action is True:
            client.lists.members.create(mlist['id'], {
                'email_address': user.email,
                'status': 'subscribed',
                'merge_fields': {
                    'FNAME': user.first_name,
                    'LNAME': user.last_name,
                },
            })
            from_email = settings.DEFAULT_FROM_EMAIL
            send_mail('South Beauty Supply Newsletter Subscription',
                      'You have subscribed to South Beauty Supply Newsletter', from_email, [user.email],
                      fail_silently=False)
            send_mail('South Beauty Supply Newsletter Subscription', str(user.first_name) + ' ' + str(
                user.last_name) + ' has subscribed to South Beauty Supply Newsletter', from_email,
                      [settings.CONTACT_EMAIL], fail_silently=False)
        else:
            try:
                client.lists.members.delete(mlist['id'], hashlib.md5(user.email).hexdigest())
                from_email = settings.DEFAULT_FROM_EMAIL
                send_mail('South Beauty Supply Newsletter Subscription',
                          'You have unsubscribed from South Beauty Supply Newsletter', from_email, [user.email],
                          fail_silently=False)
                send_mail('South Beauty Supply Newsletter Subscription', str(user.first_name) + ' ' + str(
                    user.last_name) + ' has unsubscribed from South Beauty Supply Newsletter', from_email,
                          [settings.CONTACT_EMAIL], fail_silently=False)
            except Exception as inst:
                pass


def validate_license(license, user=None):
    wholesale = WholeSale
    result = ''
    w_license = License.objects.filter(license_number=license).count()
    if w_license is 0:
        w_license = License.objects.filter(alternate_license_number=license).count()
    if w_license is 0:
        result = 'Not Valid'  # Response({'message': 'That license is not valid.'}, status=status.HTTP_409_CONFLICT)
        return result
    try:
        wholesale = WholeSale.objects.get(license=license)
        if wholesale.user != user:
            result = 'In Use'  # return Response({'message': 'License "%s" is already in use.' % license}, status=status.HTTP_409_CONFLICT)
            return result
    except wholesale.DoesNotExist:
        ''
    return result


def validate_usage(license):
    usage = WholeSale.objects.filter(license=license).count()
    if usage is 0:
        return False
    return True