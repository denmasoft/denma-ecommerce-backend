from __future__ import unicode_literals
import functools
import itertools
from six.moves import map
from django.contrib.auth.models import User
from rest_framework.response import Response
from django.core.exceptions import (PermissionDenied)
from django.shortcuts import redirect
from django.http import Http404
from oscar.core.loading import get_model, get_class
from oscarapi import serializers, permissions
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.permissions import IsAdminUser
from .mixin import PutIsPatchMixin
from django.template import RequestContext
from rest_framework.authentication import (TokenAuthentication,SessionAuthentication)
import serializers
from numbers import Number
from rest_framework.generics import (CreateAPIView, DestroyAPIView)
from rest_framework.views import APIView
from rest_framework import status, views, response, generics, exceptions
from customapi.basket.models import Basket
from customapi.products.serializers import (PriceTaxSerializer)
from customapi.partner.strategy import Selector
from customapi.cart import operations as cart_ops
from decimal import Decimal as D
from django.core.urlresolvers import reverse, NoReverseMatch
from oscarapi.permissions import IsOwner
from oscarapi.views.utils import BasketPermissionMixin
from oscarapi.signals import oscarapi_post_checkout
from oscarapi.basket.operations import assign_basket_strategy
from oscar.apps.catalogue.models import Option
from customapi.shipping.methods import SbsPrice
from customapi.address.models import UserAddress
from oscar.apps.address.models import Country
import paypalrestsdk
import logging
import stripe
import shippo
import json
from slugify import slugify
from django.conf import settings
from rest_framework import status
from oscarapi.basket import operations


shippo.api_key = settings.SHIPPO_KEY
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')
Line = get_model('basket', 'Line')


class PaymentExecute(APIView):
    def get(self, request, pk=None, format=None):
        order = get_object_or_404(Order, pk=pk)
        paymentid = request.GET.get('paymentId', '')
        payerid = request.GET.get('PayerID', '')
        payment = paypalrestsdk.Payment.find(paymentid)

        # PayerID is required to approve the payment.
        if payment.execute({"payer_id": payerid}):  # return True or False
            print("Payment[%s] execute successfully" % (payment.id))
            to_email = order.guest_email
            if order.user is not None:
                to_email = order.user.email
            tax = float(settings.TAX) * 100
            tax_value = float(order.total_incl_tax-order.shipping_incl_tax) * float(settings.TAX)
            tax_value = round(tax_value, 2)
            total = float(order.total_incl_tax) + float(tax_value)
            msg_html = render_to_string('invoice.html', {
                'total': total,
                'items': cart_ops.getitems(order),
                'discounts': cart_ops.getdiscounts(order),
                'shippings': cart_ops.getshipping(order),
                'tax_name': str(tax)+"% tax",
                'tax_value': tax_value})
            order.basket.submit()
            send_mail('Thanks for purchasing with us', msg_html, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False, html_message=msg_html)
            # send_mail('Thanks for purchasing with us', "You have purchased successfully", settings.DEFAULT_FROM_EMAIL,
              # [to_email], fail_silently=False)
            return redirect(settings.FRONT_URL+"/"+payment.id)
        else:
            print(payment.error)


class PayPalView(APIView):
    """
    payment process according to payment provider.
    """

    def getitems(self, order):
        """ """
        items = []
        currency = "USD"
        for line in order.lines.all():
            for stock in line.product.stockrecords.all():
                sku = stock.partner_sku
            currency = order.currency
            quantity = line.quantity
            strategy = Selector().strategy()
            product = get_object_or_404(Product, pk=line.product.id)
            ser = PriceTaxSerializer(
                strategy.fetch_for_product(product).price,
                context={'request': None})
            price = ser.data
            items.append({
                "name": str(line.product.title),
                "sku": str(sku),
                "price": price['incl_tax'],
                "currency": str(currency),
                "quantity": quantity,
            })
        for offer in order.discounts.all():
            items.append({
                "name": str(offer.offer_name),
                "price": str(-offer.amount),
                "currency": str(currency),
                "quantity": 1,
            })
        if order.shipping_code:
            items.append({
                "name": str(order.shipping_method),
                "price": float(order.shipping_incl_tax),
                "currency": str(currency),
                "quantity": 1,
            })
        tax = D(settings.TAX) * 100
        tax_value = float(order.total_incl_tax-order.shipping_incl_tax) * float(settings.TAX)
        tax_value = round(tax_value, 2)
        items.append({
            "name": str(tax)+"% tax",
            "price": tax_value,
            "currency": str(currency),
            "quantity": 1,
        })
        return items

    def pay(self, order):
        tax_value = float(order.total_incl_tax-order.shipping_incl_tax) * float(settings.TAX)
        tax_value = round(tax_value, 2)
        total = float(order.total_incl_tax) + float(tax_value)
        paypalrestsdk.configure({
            "mode": "sandbox",  # sandbox or live
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET, })
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"},

            # Redirect URLs
            "redirect_urls": {
                "return_url": settings.API_URL+"/paypal/" + str(order.id) + "/execute/",
                "cancel_url": settings.FRONT_URL},
            "transactions": [{
                "item_list": {
                    "items": self.getitems(order)},
                "amount": {
                    "total": ('%.2f' % total),
                    "currency": order.currency},
                "description": ""}]})

        if payment.create():
            print("Payment[%s] created successfully" % (payment.id))
            for link in payment.links:
                if link.method == "REDIRECT":
                    redirect_url = link.href
                    print("Redirect for approval: %s" % (redirect_url))
                    return redirect_url
        else:
            print(payment.error)
            raise ValueError(payment.error)

    def get(self, request, pk=None, format=None):
        order = get_object_or_404(Order, pk=pk)
        link = self.pay(order)
        return redirect(link)


class StripeChargeView(APIView):
    authentication_classes = []

    def post(self, request, pk=None, format=None):
        stripe.api_key = settings.STRIPE_API_KEY
        order = get_object_or_404(Order, pk=pk)
        to_email = order.guest_email
        if order.user is not None:
            to_email = order.user.email
        # token = stripe.Token.create(number="4242 4242 4242 4242", cvc="025", exp_month="12", exp_year="45")
        customer = stripe.Customer.create(
            email=to_email,
            source="token")
        try:
            charge = stripe.Charge.create(
                customer=customer.id,
                amount=int(order.total_incl_tax * 100),
                currency=order.currency,
                description="South Beauty Supply Charge"
            )
            charge_id = charge.id
        except stripe.CardError, ce:
            return False, ce.message
        order.basket.submit()
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail('Thanks for purchasing with us', "You have purchased successfully", from_email, [to_email],fail_silently=False)
        return redirect(settings.FRONT_URL)


class StripeView(APIView):
    def get(self, request, pk=None, format=None):
        stripe.api_key = settings.STRIPE_API_KEY
        token = request.GET.get('token','')
        order = get_object_or_404(Order, pk=pk)
        tax_value = float(order.total_incl_tax-order.shipping_incl_tax) * float(settings.TAX)
        tax_value = round(tax_value, 2)
        total = float(order.total_incl_tax) + float(tax_value)
        to_email = order.guest_email
        if order.user is not None:
            to_email = order.user.email
        # token = stripe.Token.create(number="4242 4242 4242 4242", cvc="025", exp_month="12", exp_year="45")
        customer = stripe.Customer.create(
            email=to_email,
            source=token)
        try:
            charge = stripe.Charge.create(
                customer=customer.id,
                amount=int(total * 100),
                currency=order.currency,
                description="South Beauty Supply Charge"
            )
            charge_id = charge.id
        except stripe.CardError, ce:
            return False, ce.message
        tax = float(settings.TAX) * 100
        tax_value = float(order.total_incl_tax-order.shipping_incl_tax) * float(settings.TAX)
        tax_value = round(tax_value, 2)
        total = float(order.total_incl_tax) + float(tax_value)
        msg_html = render_to_string('invoice.html', {
            'total': total,
            'items': cart_ops.getitems(order),
            'discounts': cart_ops.getdiscounts(order),
            'shippings': cart_ops.getshipping(order),
            'tax_name': str(tax)+"% tax",
            'tax_value': tax_value})
        order.basket.submit()
        send_mail('Thanks for purchasing with us', msg_html, settings.DEFAULT_FROM_EMAIL, [to_email],fail_silently=False, html_message=msg_html)
        return redirect(settings.FRONT_URL+"/"+charge_id)
        # order = get_object_or_404(Order, pk=pk)
        #  return render_to_response('stripe.html',{'order': order.id, 'amount': order.total_incl_tax * 100, 'currency': order.currency, 'key': settings.STRIPE_PUBLISH_KEY})


class CustomCartAddProduct(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    """
    Adds a product to cart.
    """

    serializer_class = serializers.CartAddProductSerializer

    def get_or_create_cart(self, request, pk):

        cart = get_object_or_404(Basket, pk=pk, owner=request.user)
        if not cart:
            carts = request.user.carts.all()[:1]
            if not carts:
                return request.user.carts.create()
                cart = carts[0]

        if not cart.is_allowed_to_edit(request.user):
            raise PermissionDenied
        return cart

    def validate(self, basket, product, quantity, options):
        availability = basket.strategy.fetch_for_product(
            product).availability

        # check if product is available at all
        if not availability.is_available_to_buy:
            return False, availability.message

        # check if we can buy this quantity
        allowed, message = availability.is_purchase_permitted(quantity)
        if not allowed:
            return False, message

        # check if there is a limit on amount
        allowed, message = basket.is_quantity_allowed(quantity)
        if not allowed:
            return False, message
        return True, None

    def get_or_create_option(self, request, name):
        try:
            option = generics.get_object_or_404(Option, name=name)
        except Http404:
            option = Option.objects.create(name=name)
        return option

    def post(self, request, pk=None, format=None):
        # p_ser = self.serializer_class(data=request.data, context={'request': request})

        product = get_object_or_404(Product, pk=request.data['id'])
        quantity = request.data['amount']
        options = request.data['options']
        basket = get_object_or_404(Basket, pk=request.data['basket'])
        basket = operations.prepare_basket(basket, request)
        basket_valid, message = self.validate(basket, product, int(quantity), options)
        if not basket_valid:
            return Response({'response': '406', 'message': message}, status=status.HTTP_406_NOT_ACCEPTABLE)
        quantity = quantity if int(quantity) else 1
        items = []
        for option in options:
            opt = self.get_or_create_option(request, option['option'])
            items.append({'option': opt, 'value': option['value']})            
        basket.add_product(product, quantity, items)
        operations.apply_offers(request, basket)
        return Response({'cart': basket.id}, status=status.HTTP_200_OK)

        # return Response(status=status.HTTP_406_NOT_ACCEPTABLE)


class CustomCartRemoveProduct(DestroyAPIView):
    """
    Removes a product from a cart.
    """

    serializer_class = serializers.CartRemoveProductSerializer

    def validate(self, basket, product, quantity, options):
        availability = basket.strategy.fetch_for_product(
            product).availability

        # check if product is available at all
        if not availability.is_available_to_buy:
            return False, availability.message

        # check if we can buy this quantity
        allowed, message = availability.is_purchase_permitted(quantity)
        if not allowed:
            return False, message

        # check if there is a limit on amount
        allowed, message = basket.is_quantity_allowed(quantity)
        if not allowed:
            return False, message
        return True, None

    def get_or_create_option(self, request, name):
        try:
            option = generics.get_object_or_404(Option, name=name)
        except Http404:
            option = Option.objects.create(name=name)
        return option

    def post(self, request, pk=None, format=None):
        options = []
        if 'options' in request.data:
            options = request.data['options']
        product = get_object_or_404(Product, pk=request.data['id'])
        basket = get_object_or_404(Basket, pk=request.data['basket'])
        basket = operations.prepare_basket(basket, request)
        quantity = 0
        if 'amount' in request.data:
            quantity = request.data['amount']
        basket_valid, message = self.validate(basket, product, int(quantity), options)
        if not basket_valid:
            return Response({'response': '406', 'message': message}, status=status.HTTP_406_NOT_ACCEPTABLE)
        items = []
        for option in options:
            opt = self.get_or_create_option(request, option['option'])
            items.append({'option': opt, 'value': option['value']})            
        basket.remove(product, quantity, items)
        return Response("")


class CartCheckoutView(BasketPermissionMixin, views.APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    """
    Prepare an order for checkout.

    POST(basket, shipping_address,
         [total, shipping_method_code, shipping_charge, billing_address]):
    {
        "basket": "http://testserver/oscarapi/baskets/1/",
        "guest_email": "foo@example.com",
        "total": "100.0",
        "shipping_charge": {
            "currency": "EUR",
            "excl_tax": "10.0",
            "tax": "0.6"
        },
        "shipping_method_code": "no-shipping-required",
        "shipping_address": {
            "country": "http://127.0.0.1:8000/oscarapi/countries/NL/",
            "first_name": "Henk",
            "last_name": "Van den Heuvel",
            "line1": "Roemerlaan 44",
            "line2": "",
            "line3": "",
            "line4": "Kroekingen",
            "notes": "Niet STUK MAKEN OK!!!!",
            "phone_number": "+31 26 370 4887",
            "postcode": "7777KK",
            "state": "Gerendrecht",
            "title": "Mr"
        }
    }
    returns the order object.
    """
    order_serializer_class = serializers.CustomOrderSerializer
    serializer_class = serializers.CustomCheckoutSerializer

    def post(self, request, format=None):
        # TODO: Make it possible to create orders with options.
        # at the moment, no options are passed to this method, which means they
        # are also not created.     
        checkout_data = request.data 
        usr = checkout_data['user']
        usr = int(usr)
        if usr is not 0:            
            ruser = get_object_or_404(User, pk=usr)
            request.user = ruser            
        shipping_address_country = checkout_data['shipping_address_country']
        shipping_address_country_iso_3166_1_a2 = checkout_data['shipping_address_country_iso_3166_1_a2']
        shipping_address_first_name = checkout_data['shipping_address_first_name']
        shipping_address_last_name =checkout_data['shipping_address_last_name']
        shipping_address_line1 = checkout_data['shipping_address_line1']
        shipping_address_notes = checkout_data['shipping_address_notes']
        shipping_address_postcode = checkout_data['shipping_address_postcode']
        shipping_address_state = checkout_data['shipping_address_state']
        shipping_address_id = checkout_data['shipping_address_id']

        delivery_address_country = checkout_data['delivery_address_country']
        delivery_address_country_iso_3166_1_a2 = checkout_data['delivery_address_country_iso_3166_1_a2']
        delivery_address_first_name = checkout_data['delivery_address_first_name']
        delivery_address_last_name = checkout_data['delivery_address_last_name']
        delivery_address_line1 = checkout_data['delivery_address_line1']
        delivery_address_notes = checkout_data['delivery_address_notes']
        delivery_address_postcode = checkout_data['delivery_address_postcode']
        delivery_address_state = checkout_data['delivery_address_state']
        delivery_address_id = checkout_data['delivery_address_id']

        shipping_method_code =checkout_data['shipping_method_code']
        shipping_method_name =checkout_data['shipping_method_name']
        shipping_method_cost =checkout_data['shipping_method_cost']
        
        SbsPrice(shipping_method_cost, shipping_method_cost, shipping_method_code, shipping_method_code)

        basket_data = {
            "basket": checkout_data['basket'],
            "shipping_method_code": shipping_method_code,            
            "shipping_address": {
                "country": shipping_address_country,
                "first_name": shipping_address_first_name,
                "last_name": shipping_address_last_name,
                "line1": shipping_address_line1,
                "line2": "",
                "line3": "",
                "line4": "",
                "notes": shipping_address_notes,        
                "postcode": shipping_address_postcode,
                "state": shipping_address_state,
                "title": ""
            }
        }
        if 'guest_email' in checkout_data:
            basket_data['guest_email'] = checkout_data['guest_email']
        if usr is not 0:      
            if shipping_address_id is None:
                user = User.objects.get(pk=usr)
                country = get_object_or_404(Country, iso_3166_1_a2=shipping_address_country_iso_3166_1_a2)
                user_address = UserAddress.objects.create(user=user,
                                                      line1=shipping_address_line1,
                                                      state=shipping_address_state,
                                                      postcode=shipping_address_postcode,
                                                      country=country)
                user_address.save()
            if delivery_address_id is None:
                user = User.objects.get(pk=usr)
                country = get_object_or_404(Country, iso_3166_1_a2=delivery_address_country_iso_3166_1_a2)
                user_address = UserAddress.objects.create(user=user,
                                                      line1=delivery_address_line1,
                                                      state=delivery_address_state,
                                                      postcode=delivery_address_postcode,
                                                      country=country)
                user_address.save()
        data_basket = self.get_data_basket(basket_data, format)
        basket = generics.get_object_or_404(Basket.objects, pk=data_basket.pk)
        # basket = self.check_basket_permission(request, basket_pk=data_basket.pk)

        # by now an error should have been raised if someone was messing
        # around with the basket, so asume invariant
        # assert (data_basket == basket)

        c_ser = self.serializer_class(data=basket_data, context={'request': request})
        if c_ser.is_valid():
            order = c_ser.save()
            order.shipping_code = slugify(shipping_method_code)
            order.shipping_excl_tax = shipping_method_cost
            order.shipping_incl_tax = shipping_method_cost
            order.shipping_method = slugify(shipping_method_code)
            order.total_excl_tax = float(shipping_method_cost) + float(order.total_excl_tax)
            order.total_incl_tax = float(shipping_method_cost) + float(order.total_incl_tax)
            order.save()
            basket.freeze()
            o_ser = self.order_serializer_class(order, context={'request': request})
            oscarapi_post_checkout.send(sender=self, order=order, user=request.user, request=request, response=response)
            return response.Response(o_ser.data)

        return response.Response(c_ser.errors, status.HTTP_406_NOT_ACCEPTABLE)


class CustomBasketView(APIView):
    """
    Api for retrieving a user's basket.

    GET:
    Retrieve your basket.
    """
    serializer_class = serializers.CustomBasketSerializer

    def get(self, request, format=None):
        basket = operations.get_basket(request)
        ser = self.serializer_class(basket, context={'request': request})
        return Response(ser.data)


class CustomBasketDetail(PutIsPatchMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.CustomBasketSerializer
    # permission_classes = (permissions.IsAdminUserOrRequestContainsBasket,)
    queryset = Basket.objects.all()

    def get_object(self):
        basket = super(CustomBasketDetail, self).get_object()
        return assign_basket_strategy(basket, self.request)


class CustomLineList(BasketPermissionMixin, generics.ListCreateAPIView):
    """
    Api for adding lines to a basket.

    Permission will be checked,
    Regular users may only access their own basket,
    staff users may access any basket.

    GET:
    A list of basket lines.

    POST(basket, line_reference, product, stockrecord,
         quantity, price_currency, price_excl_tax, price_incl_tax):
    Add a line to the basket, example::

        {
            "basket": "http://127.0.0.1:8000/oscarapi/baskets/100/",
            "line_reference": "234_345",
            "product": "http://127.0.0.1:8000/oscarapi/products/209/",
            "stockrecord":
                "http://127.0.0.1:8000/oscarapi/stockrecords/100/",
            "quantity": 3,
            "price_currency": "EUR",
            "price_excl_tax": "100.0",
            "price_incl_tax": "121.0"
        }
    """
    serializer_class = serializers.CustomLineSerializer
    queryset = Line.objects.all()

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        if pk is not None:  # usually we need the lines of the basket
            basket = self.check_basket_permission(self.request, basket_pk=pk)
            prepped_basket = operations.assign_basket_strategy(
                basket, self.request)
            return prepped_basket.all_lines()
        elif self.request.user.is_staff:  # admin users can view a bit more
            return super(CustomLineList, self).get_queryset()
        else:  # non admin users can view nothing at all here.
            return self.permission_denied(self.request)

    def get(self, request, pk=None, format=None):
        if pk is not None:
            basket = self.check_basket_permission(request, pk)
            prepped_basket = operations.assign_basket_strategy(basket, request)
            self.queryset = prepped_basket.all_lines()
            self.serializer_class = serializers.CustomBasketLineSerializer

        return super(CustomLineList, self).get(request, format)

    def post(self, request, pk=None, format=None):
        data_basket = self.get_data_basket(request.data, format)
        self.check_basket_permission(request, basket=data_basket)

        if pk is not None:
            url_basket = self.check_basket_permission(request, basket_pk=pk)
            if url_basket != data_basket:
                raise exceptions.NotAcceptable(
                    _('Target basket inconsistent %s != %s') % (
                        url_basket.pk, data_basket.pk
                    )
                )
        elif not request.user.is_staff:
            self.permission_denied(request)

        return super(CustomLineList, self).post(request, format=format)

class CartCheckout(APIView):
    """
    Adds a product to cart.
    """

    serializer_class = serializers.CartAddProductSerializer

    def get_or_create_cart(self, request, pk):

        cart = get_object_or_404(Basket, pk=pk, owner=request.user)
        if not cart:
            carts = request.user.carts.all()[:1]
            if not carts:
                return request.user.carts.create()
                cart = carts[0]

        if not cart.is_allowed_to_edit(request.user):
            raise PermissionDenied
        return cart

    def validate(self, basket, product, quantity, options):
        availability = basket.strategy.fetch_for_product(
            product).availability

        # check if product is available at all
        if not availability.is_available_to_buy:
            return False, availability.message

        # check if we can buy this quantity
        allowed, message = availability.is_purchase_permitted(quantity)
        if not allowed:
            return False, message

        # check if there is a limit on amount
        allowed, message = basket.is_quantity_allowed(quantity)
        if not allowed:
            return False, message
        return True, None

    def get_or_create_option(self, request, name):
        try:
            option = generics.get_object_or_404(Option, name=name)
        except Http404:
            option = Option.objects.create(name=name)
        return option

    def post(self, request, pk=None, format=None):
        
        ValueError(request);
        return;    
        product = get_object_or_404(Product, pk=request.data['id'])
        quantity = request.data['amount']
        options = request.data['options']
        basket = operations.get_basket(request)
        basket_valid, message = self.validate(basket, product, int(quantity), options)
        if not basket_valid:
            return Response({'response': '406', 'message': message}, status=status.HTTP_406_NOT_ACCEPTABLE)
        quantity = quantity if int(quantity) else 1
        items = []
        for option in options:
            opt = self.get_or_create_option(request, option['option'])
            items.append({'option': opt, 'value': option['value']})
            print(items)
        basket.add_product(product, quantity, items)
        operations.apply_offers(request, basket)
        return Response({'response': '200', 'message': 'added to cart'}, status=status.HTTP_200_OK)

        # return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

class CartShippingRates(APIView):
    """
    Adds a product to cart.
    """    

    def post(self, request, format=None):
        params = request.data
        #AQUI----
        #address_from = shippo.Address.retrieve("592a06aeeacd4d759ec7685830be3fd4")
        #address_from = address_from.object_id
        #parcel = shippo.Parcel.all().results[0].object_id


        #address_to = {
        #    "name": request.data['name'],
        #    "street1": request.data['street1'],
        #    "state": request.data['state'],
        #    "zip": request.data['zip'],
        #    "country": request.data['country'],
        #}
        #shipment = shippo.Shipment.create(
        #   address_from=address_from,
        #   address_to=address_to,
        #  parcels=[parcel],
        #   async=False
        #)
        #rates = shipment.rates
        result = [{"description":"Flat Rate","image":"","amount":"13.50","provider":"SBS","attributes":["FLAT"],"name":"FLAT RATE"}]
        #for rate in rates:
        #    result.append({
        #        "provider": rate.provider,
        #        "amount": rate.amount,
        #        "name": rate.servicelevel.name,
        #        "description": rate.duration_terms,
        #        "image": rate.provider_image_75,
        #        "attributes": rate.attributes
        #    })
        return Response(result)

        # return Response(status=status.HTTP_406_NOT_ACCEPTABLE)