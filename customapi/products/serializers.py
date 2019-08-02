# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers as rest_serializers
from oscarapi.serializers import (ProductSerializer, AvailabilitySerializer)
from oscarapi.utils import (OscarModelSerializer)
from rest_framework import serializers
from oscarapi.utils import (OscarModelSerializer, OscarHyperlinkedModelSerializer)
from oscar.core.loading import get_class
from oscar.core.loading import get_model
from oscar.apps.catalogue.reviews.models import ProductReview
from oscar.apps.catalogue.models import Category
from oscar.apps.catalogue.models import Product
from oscar.apps.catalogue.models import ProductAttribute
from oscar.apps.catalogue.models import ProductImage
from oscar.apps.catalogue.models import ProductAttributeValue
from oscar.apps.catalogue.models import Option
from oscar.apps.catalogue.models import ProductRecommendation
from oscar.apps.catalogue.models import ProductClass
from oscar.apps.catalogue.models import AttributeOption
from oscar.apps.catalogue.models import AttributeOptionGroup
from oscarapi.serializers.fields import TaxIncludedDecimalField
from oscar.apps.offer.models import ConditionalOffer
from oscar.apps.offer.models import Condition
from oscar.apps.offer.models import Benefit
from oscar.apps.offer.models import Range
from customapi.partner.strategy import Selector

StockRecord = get_model('partner', 'StockRecord')
Partner = get_model('partner', 'Partner')
User = get_user_model()


class OptionsSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = ('name', 'type')


class ProductLinkSerializer(ProductSerializer):
    price = rest_serializers.SerializerMethodField()
    availability = rest_serializers.SerializerMethodField()

    def get_price(self, instance):
        strategy = Selector().strategy()
        ser = PriceTaxSerializer(
            strategy.fetch_for_product(instance).price,
            context={'request': None})
        return ser.data

    def get_availability(self, instance):
        strategy = Selector().strategy()
        ser = AvailabilitySerializer(
            strategy.fetch_for_product(instance).availability,
            context={'request': None})
        return ser.data

    class Meta(ProductSerializer.Meta):
        fields = ('url',
                  'id',
                  'title',
                  'is_discountable',
                  'images',
                  'description',
                  'recommended_products',
                  'rating',
                  'date_created',
                  'date_updated',
                  'categories',
                  'attributes',
                  'price',
                  'availability'
                  )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (User.USERNAME_FIELD, 'id', 'date_joined', 'first_name', 'last_name', 'email')


class ProductReviewSerializer(OscarModelSerializer):
    user = UserSerializer(required=False)

    class Meta:
        model = ProductReview
        fields = ('product', 'score', 'title', 'body', 'user')


class CategorySerializer(OscarModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductClassSerializer(OscarModelSerializer):
    class Meta:
        model = ProductClass
        fields = '__all__'


class AttributeOptionGroupSerializer(OscarModelSerializer):
    class Meta:
        model = AttributeOptionGroup
        fields = '__all__'


class AttributeOptionSerializer(OscarModelSerializer):
    group = AttributeOptionGroupSerializer(required=False)

    class Meta:
        model = AttributeOption
        fields = '__all__'


class ProductAttributeSerializer(OscarModelSerializer):
    product_class = ProductClassSerializer(required=False)
    option_group = AttributeOptionGroupSerializer(required=False)

    class Meta:
        model = ProductAttribute
        fields = ("id", "name", "code", "type", "required",
                  "product_class", "option_group")


class ProductRecommendationSerializer(OscarModelSerializer):
    class Meta:
        model = ProductRecommendation
        fields = '__all__'


class ProductOptionsSerializer(OscarModelSerializer):
    class Meta:
        model = Option
        fields = '__all__'


class ProductImageSerializer(OscarModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'


class OptionSerializer(OscarModelSerializer):
    class Meta:
        model = Option
        fields = ('url', 'id', 'name', 'code', 'type')


class ProductAttributeValueSerializer(OscarModelSerializer):
    name = serializers.StringRelatedField(source="attribute")
    value = serializers.StringRelatedField()

    # attribute = ProductAttributeSerializer(required=False)

    class Meta:
        model = ProductAttributeValue
        fields = ('id', 'name', 'value')


class ProductImageSerializer(OscarModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'


class OptionSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = ('url', 'id', 'name', 'code', 'type')


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = '__all__'


class StockRecordSerializer(serializers.ModelSerializer):
    partner = PartnerSerializer(required=False)

    class Meta:
        model = StockRecord
        fields = '__all__'


class RecommmendedProductSerializer(OscarModelSerializer):
    price = rest_serializers.SerializerMethodField()
    availability = rest_serializers.SerializerMethodField()
    #reviews = serializers.SerializerMethodField()

    def get_price(self, instance):
        strategy = Selector().strategy()
        ser = PriceTaxSerializer(
            strategy.fetch_for_product(instance).price,
            context={'request': None})
        return ser.data

    def get_availability(self, instance):
        strategy = Selector().strategy()
        ser = AvailabilitySerializer(
            strategy.fetch_for_product(instance).availability,
            context={'request': None})
        return ser.data

    #def get_reviews(self, instance):
    #    qs = ProductReview.objects.filter(status=1, product=instance)
    #    serializer = ProductReviewSerializer(instance=qs, many=True, required=False)
    #    return serializer.data
    url = serializers.HyperlinkedIdentityField(view_name='product-detail')
    stockrecords = StockRecordSerializer(many=True, required=False)
    #attributes = ProductAttributeValueSerializer(many=True, required=False, source="attribute_values")
    #categories = CategorySerializer(many=True, required=False)
    #product_class = serializers.StringRelatedField(required=False)
    images = ProductImageSerializer(many=True, required=False)
    # price = serializers.HyperlinkedIdentityField(view_name='product-price-tax')
    # availability = serializers.HyperlinkedIdentityField(view_name='product-availability')
    #options = OptionSerializer(many=True, required=False)
    #recommended_products = RecommmendedProductSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            'url', 'id', 'title', 'description', 'rating',
            'stockrecords', 'images', 'price', 'availability')


class ProductSerializer(OscarModelSerializer):
    price = rest_serializers.SerializerMethodField()
    availability = rest_serializers.SerializerMethodField()

    def get_price(self, instance):
        strategy = Selector().strategy()
        ser = PriceTaxSerializer(
            strategy.fetch_for_product(instance).price,
            context={'request': None})
        return ser.data

    def get_availability(self, instance):
        strategy = Selector().strategy()
        ser = AvailabilitySerializer(
            strategy.fetch_for_product(instance).availability,
            context={'request': None})
        return ser.data

    url = serializers.HyperlinkedIdentityField(view_name='product-detail')
    stockrecords = StockRecordSerializer(many=True, required=False)
    attributes = ProductAttributeValueSerializer(many=True, required=False, source="attribute_values")
    categories = serializers.StringRelatedField(many=True, required=False)
    product_class = serializers.StringRelatedField(required=False)
    images = ProductImageSerializer(many=True, required=False)
    # price = serializers.HyperlinkedIdentityField(view_name='product-price-tax')
    # availability = serializers.HyperlinkedIdentityField(view_name='product-availability')
    options = OptionSerializer(many=True, required=False)
    # recommended_products = RecommmendedProductSerializer(many=True, required=False)
    reviews = ProductReviewSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            'url', 'id', 'title', 'description', 'reviews',
            'date_created', 'date_updated',
            'attributes', 'categories', 'product_class', 'rating',
            'stockrecords', 'images', 'price', 'availability', 'options')


class ProdSerializer(OscarModelSerializer):
    price = rest_serializers.SerializerMethodField()
    availability = rest_serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    def get_price(self, instance):
        strategy = Selector().strategy()
        ser = PriceTaxSerializer(
            strategy.fetch_for_product(instance).price,
            context={'request': None})
        return ser.data

    def get_availability(self, instance):
        strategy = Selector().strategy()
        ser = AvailabilitySerializer(
            strategy.fetch_for_product(instance).availability,
            context={'request': None})
        return ser.data

    def get_reviews(self, instance):
        qs = ProductReview.objects.filter(status=1, product=instance)
        serializer = ProductReviewSerializer(instance=qs, many=True, required=False)
        return serializer.data
    url = serializers.HyperlinkedIdentityField(view_name='product-detail')
    stockrecords = StockRecordSerializer(many=True, required=False)
    attributes = ProductAttributeValueSerializer(many=True, required=False, source="attribute_values")
    #categories = CategorySerializer(many=True, required=False)
    product_class = serializers.StringRelatedField(required=False)
    images = ProductImageSerializer(many=True, required=False)
    # price = serializers.HyperlinkedIdentityField(view_name='product-price-tax')
    # availability = serializers.HyperlinkedIdentityField(view_name='product-availability')
    options = OptionSerializer(many=True, required=False)
    recommended_products = RecommmendedProductSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            'url', 'id', 'title', 'description', 'reviews',
            'date_created', 'date_updated',
            'attributes', 'categories', 'product_class', 'rating',
            'stockrecords', 'images', 'price', 'availability', 'options', 'recommended_products', 'parent')


class PriceTaxSerializer(serializers.Serializer):
    currency = serializers.CharField(
        max_length=12, default=settings.OSCAR_DEFAULT_CURRENCY, required=False)
    excl_tax = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=True)
    incl_tax = TaxIncludedDecimalField(
        excl_tax_field='excl_tax',
        decimal_places=2, max_digits=12, required=False)
    tax = TaxIncludedDecimalField(
        excl_tax_value=settings.TAX,
        decimal_places=2, max_digits=12, required=False)