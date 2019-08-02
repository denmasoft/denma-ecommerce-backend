# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from oscarapi.basket.operations import get_basket, apply_offers
from rest_framework import generics, exceptions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import (PermissionDenied)
from rest_framework.authentication import (TokenAuthentication, SessionAuthentication)
from django.utils.translation import ugettext_lazy as _
from customapi.wishlists.models import WishList
from oscar.core.loading import get_class, get_classes
from oscar.core.loading import get_model
from oscarapi import serializers, permissions
from oscarapi.views.mixin import PutIsPatchMixin
from django.shortcuts import get_object_or_404
import utils
import serializers
import permissions
from rest_framework.generics import (CreateAPIView,DestroyAPIView)

from rest_framework.authtoken.models import Token

__all__ = ('WishListView', 'WishListLineList',
           'WishListLineDetail', 'AddProductToWishlist',
           'AddToBasketFromWishlist', 'CustomWishListAddProduct')
Line = get_model('wishlists', 'Line')
Product = get_model('catalogue', 'Product')
WishListForm, LineFormset = get_classes('wishlists.forms',
                                        ['WishListForm', 'LineFormset'])
PageTitleMixin = get_class('customer.mixins', 'PageTitleMixin')
def get_wishlist(request):
    # Get wishlist for user
    try:
        wishlist, _ = WishList.objects.get_or_create(
            owner=request.user, visibility=WishList.PRIVATE)
    except WishList.MultipleObjectsReturned:
        wishlist = WishList.objects.filter(owner=request.user).latest('id')
    return wishlist


class WishListView(APIView):
    """
    Api for retrieving a user's wishlist.
    GET:
    Retrieve your wishlist.
    """
    permission_classes = (IsAuthenticated,)


    def get(self,request,format=None):
        wishlist = get_wishlist(request)
        ser = serializers.WishListSerializer(wishlist, context={'request': request})
        return Response(ser.data)


class WishListLineList(utils.WishListPermissionMixin, generics.ListCreateAPIView):
    """
    Api for adding lines to a wishlist.

    Permission will be checked,
    Regular users may only access their own wishlist,
    staff users may access any wishlist.

    GET:
    A list of wishlist lines.

    POST(wishlist, line_reference, product, stockrecord,
         quantity, price_currency, price_excl_tax, price_incl_tax):
    Add a line to the wishlist, example::

        {
            "wishlist": "http://127.0.0.1:8000/oscarapi/wishlists/100/",
            "product": "http://127.0.0.1:8000/oscarapi/products/209/",
            "quantity": 3,
            "title": "test",
        }
    """
    queryset = Line.objects.filter(product__isnull=False)
    serializer_class = serializers.WishListLineSerializer


    def get(self,request, pk=None, format=None):
        if pk is not None:
            self.check_wishlist_permission(request, pk)
            self.queryset = self.queryset.filter(wishlist__id=pk)
        elif not request.user.is_staff:
            self.permission_denied(request)

        return super(WishListLineList, self).get(request, format)


    def post(self, request, pk=None, format=None):

        data_wishlist = self.get_data_wishlist(request.data, format)
        self.check_wishlist_permission(request, wishlist=data_wishlist)

        print data_wishlist
        print request.data
        print pk

        if pk is not None:
            url_wishlist = self.check_wishlist_permission(
                request, wishlist_pk=pk)

            if url_wishlist != data_wishlist:
                raise exceptions.NotAcceptable(
                    _('Target wishlist inconsistent %s != %s') % (
                        url_wishlist.pk, data_wishlist.pk
                    )
                )
        elif not request.user.is_staff:
            self.permission_denied(request)

        return super(WishListLineList, self).post(request, format=format)


class WishListLineDetail(PutIsPatchMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Line.objects.all()
    serializer_class = serializers.WishListLineSerializer
    permission_classes = (permissions.IsAdminUserOrRequestContainsWishListLine,)


class AddProductToWishlist(APIView):
    authentication_classes = (TokenAuthentication,)
    """
    Add a product to the wishlist.

    POST(url)
    {
        "url": "http://testserver.org/oscarapi/products/209/",
    }
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        add_ser = serializers.AddProductFromWishListSerializer(
            data=request.data, context={'request': request})

        print add_ser
        if add_ser.is_valid():
            wishlist = get_wishlist(request)

            product = add_ser.object
            wishlist.add(product)
            ser = serializers.WishListSerializer(
                wishlist, context={'request': request})
            return Response(ser.data)
        return Response({'reason': add_ser.errors},
                        status=status.HTTP_406_NOT_ACCEPTABLE)


class AddToBasketFromWishlist(APIView):
    authentication_classes = (TokenAuthentication,)
    """
    Add a product from wishlist to basket.

    POST(url)
    {
        "url": "http://testserver.org/oscarapi/wishlistlines/33/",
    }
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        l_ser = serializers.AddProductFromWishListSerializer(
            data=request.DATA, context={'request': request})
        if l_ser.is_valid():
            basket = get_basket(request)
            line = l_ser.object
            product = line.product
            quantity = line.quantity

            availability = basket.strategy.fetch_for_product(
                product).availability

            # check if product is available at all
            if not availability.is_available_to_buy:
                return Response(
                    {'reason': availability.message},
                    status=status.HTTP_406_NOT_ACCEPTABLE)

            # check if we can buy this quantity
            allowed, message = availability.is_purchase_permitted(quantity)
            if not allowed:
                return Response({'reason': message},
                                status=status.HTTP_406_NOT_ACCEPTABLE)

            # check if there is a limit on amount
            allowed, message = basket.is_quantity_allowed(quantity)
            if not allowed:
                return Response({'reason': message},
                                status=status.HTTP_406_NOT_ACCEPTABLE)

            basket.add_product(product, quantity=quantity)
            apply_offers(request, basket)
            line.delete()
            ser = serializers.BasketSerializer(
                basket, context={'request': request})
            return Response(ser.data)

        return Response(
            {'reason': l_ser.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)


class CustomWishListAddProduct(CreateAPIView):
    authentication_classes = (TokenAuthentication,)
    """
    Adds a product to a wish list.

    - If the user doesn't already have a wishlist then it will be created for
      them.
    - If the product is already in the wish list, its quantity is increased.
    """

    serializer_class = serializers.WishListCustomSerializer

    def get_or_create_wishlist(self, request, pk):

        wishlist = get_object_or_404(WishList, pk=pk, owner=request.user)
        if not wishlist:
            wishlists = request.user.wishlists.all()[:1]
            if not wishlists:
                return request.user.wishlists.create()
                wishlist = wishlists[0]

        if not wishlist.is_allowed_to_edit(request.user):
            raise PermissionDenied
        return wishlist

    def post(self, request, pk=None, format=None):
        product = get_object_or_404(Product, pk=request.data['product'])
        wishlist = self.get_or_create_wishlist(request, pk)
        wishlist.add(product, request.data['title'], request.data['quantity'])
        # msg = _("'%s' was added to your wish list.") % product.get_title()
        # messages.success(self.request, msg)
        # return redirect_to_referrer(self.request, product.get_absolute_url())
        return Response({'response': '200', 'message': 'added to wishlist'}, status=status.HTTP_200_OK)


class CustomWishListAddProd(CreateAPIView):
    authentication_classes = (TokenAuthentication,)
    """
    Adds a product to a wish list.

    - If the user doesn't already have a wishlist then it will be created for
      them.
    - If the product is already in the wish list, its quantity is increased.
    """

    serializer_class = serializers.WishListCustomSerializer

    def get_or_create_wishlist(self, request):
        try:
            wishlist, _ = WishList.objects.get_or_create(
                owner=request.user, visibility=WishList.PRIVATE)
        except WishList.MultipleObjectsReturned:
            wishlist = WishList.objects.filter(owner=request.user).latest('id')
        return wishlist

    def post(self, request, pk=None, format=None):
        product = get_object_or_404(Product, pk=request.data['id'])
        token = request.data['token']
        tokken = Token
        user = None
        try:
            tokken = Token.objects.get(key=token)
            request.user = tokken.user
        except tokken.DoesNotExist:
               ''
        wishlist = self.get_or_create_wishlist(request)
        wishlist.add(product, request.data['title'], request.data['amount'])
        # msg = _("'%s' was added to your wish list.") % product.get_title()
        # messages.success(self.request, msg)
        # return redirect_to_referrer(self.request, product.get_absolute_url())
        return Response({'response': '200', 'message': 'added to wishlist'}, status=status.HTTP_200_OK)


class CustomWishListRemoveProduct(DestroyAPIView):
    authentication_classes = (TokenAuthentication,)
    """
    Removes a product from a wish list.
    """

    serializer_class = serializers.WishListRemoveProductSerializer

    def post(self, request, pk=None, format=None):
        product = get_object_or_404(Product, pk=request.data['product'])
        wishlist = get_object_or_404(WishList, pk=pk)
        if not wishlist.is_allowed_to_edit(request.user):
            raise PermissionDenied
        wishlist.remove(product)
        return Response("")


class CustomWishListRemoveProd(DestroyAPIView):
    authentication_classes = (TokenAuthentication,)
    """
    Removes a product from a wish list.
    """

    serializer_class = serializers.WishListRemoveProductSerializer

    def get_or_create_wishlist(self, request):
        try:
            wishlist, _ = WishList.objects.get_or_create(
                owner=request.user, visibility=WishList.PRIVATE)
        except WishList.MultipleObjectsReturned:
            wishlist = WishList.objects.filter(owner=request.user).latest('id')
        return wishlist

    def post(self, request, pk=None, format=None):
        token = request.data['token']
        tokken = Token
        token_user = None
        try:
            tokken = Token.objects.get(key=token)
            request.user = tokken.user
        except tokken.DoesNotExist:
            pass    
        product = get_object_or_404(Product, pk=request.data['id'])
        wishlist = self.get_or_create_wishlist(request)
        if not wishlist.is_allowed_to_edit(request.user):
            raise PermissionDenied
        wishlist.remove(product)
        return Response({'response': '200', 'message': 'removed from wishlist'}, status=status.HTTP_200_OK)
