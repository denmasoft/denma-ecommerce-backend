# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers
from customapi.wishlists.models import WishList
from customapi.products.serializers import ProductSerializer,UserSerializer
from oscar.apps.catalogue.models import Product
from oscarapi.utils import (
    OscarHyperlinkedModelSerializer
)
from oscar.core.loading import get_model
Line = get_model('wishlists', 'Line')
LineAttribute = get_model('basket', 'LineAttribute')
Option = get_model('catalogue', 'Option')


class OptionSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'name']


class LineAttributeSerializer(OscarHyperlinkedModelSerializer):
    option = OptionSerializer(required=True)

    class Meta:
        model = LineAttribute
        fields = ['url', 'option', 'value']


class WishListLineSerializer(serializers.HyperlinkedModelSerializer):

    product = ProductSerializer(required=True)
    attributes = LineAttributeSerializer(
        many=True,
        required=False,
        read_only=True)

    class Meta:
        model = Line
        fields = ['product', 'id', 'quantity', 'attributes']


class WishListSerializer(serializers.HyperlinkedModelSerializer):

    owner = UserSerializer(required=False)
    lines = WishListLineSerializer(many=True, required=True)

    class Meta:
        model = WishList
        fields = ['url', 'id', 'lines', 'owner', 'visibility', 'date_created']


class WishListCustomSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedRelatedField(view_name='product-detail', queryset=Product.objects, required=True)

    class Meta:
        model = Line
        fields = ['product', 'id', 'title', 'quantity']


class WishListRemoveProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Line
        fields = ['product']


class AddProductFromWishListSerializer(serializers.Serializer):
    url = serializers.HyperlinkedRelatedField(
        view_name='wishlistline-detail', queryset=Line.objects,
        required=True)

    class Meta:
        model = Line
        fields = ['url']

    def update(self,instance,validated_data):
        if instance is not None:
            return instance
        return validated_data['url']

    def create(self, validated_data):
        return Line.objects.create(**validated_data)
