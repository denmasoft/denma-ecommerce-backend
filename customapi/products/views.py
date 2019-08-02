# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.models import (User, AnonymousUser)
import django_filters
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from oscarapi.views import basic
from rest_framework import generics
from rest_framework.response import Response
from oscar.core.loading import get_model, get_class
from oscarapi import serializers
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db.models import Max
import serializers
from rest_framework.views import APIView
from rest_framework import status
from oscar.apps.catalogue.reviews.models import ProductReview
from customapi.products.serializers import (ProductLinkSerializer, ProductSerializer, PriceTaxSerializer,
                                            OptionsSerializer, ProdSerializer)
from customapi.partner.strategy import Selector
from customapi.categories import operations as cat_ops
from oscar.apps.offer.models import ConditionalOffer

Product = get_model('catalogue', 'Product')
ProductRecommendation = get_model('catalogue', 'ProductRecommendation')
Option = get_model('catalogue', 'Option')
Category = get_model('catalogue', 'Category')
from rest_framework.authtoken.models import Token


class OptionList(generics.CreateAPIView):
    queryset = Option.objects.all()
    serializer_class = OptionsSerializer


class ProductList(basic.ProductList):
    serializer_class = ProductSerializer


class ProductDetail(generics.ListAPIView):

    def recommended_products(self, product, request, pivot=[]):
        rec_prods = []
        recommended = ProductRecommendation.objects.filter(primary=product)
        for pr in recommended:
            if pr.recommendation.id not in pivot:
                pr_data = ProdSerializer(pr.recommendation, context={'request': request})
                rec_prods.append(pr_data.data)
                pivot.append(pr.recommendation.id)
                rec_prods += self.recommended_products(pr.recommendation, request, pivot)
        recommended = ProductRecommendation.objects.filter(recommendation=product)
        for pr in recommended:
            if pr.primary.id not in pivot:
                pr_data = ProdSerializer(pr.primary, context={'request': request})
                rec_prods.append(pr_data.data)
                pivot.append(pr.primary.id)
                rec_prods += self.recommended_products(pr.primary, request, pivot)
        return rec_prods

    def get(self, request, pk=None, format=None):
        product = get_object_or_404(Product, pk=pk)
        ser = ProdSerializer(product, context={'request': request})
        categories = ser.data['categories']
        prodcat = categories[0]
        prodcat = get_object_or_404(Category, pk=prodcat)
        pivot = []
        pivot.append(product.id)
        recommended = self.recommended_products(product, request, pivot)
        recommended_products = []
        for rec in recommended:
            recommended_products.append(rec)
            #product = get_object_or_404(Product, pk=rec['id'])
            #recommended_products += self.recommended_products(product, request)

        #recommended_products = []
        #recommended = ProductRecommendation.objects.filter(recommendation=product)
        #for pr in recommended:
        #    pr_data = ProductSerializer(pr.primary, context={'request': request})
        #    recommended_products.append(
        #        {'url': pr_data.data['url'], 'id': pr_data.data['id'], 'title': pr_data.data['title'],
        #         'description': pr_data.data['description'],
        #         'rating': pr_data.data['rating'],
        #         'stockrecords': pr_data.data['stockrecords'], 'images': pr_data.data['images'],
        #         'price': pr_data.data['price'], 'availability': pr_data.data['availability'],
        #         })
        #for rc_prod in ser.data['recommended_products']:
        #    recommended_products.append(
        #        {'url': rc_prod['url'], 'id': rc_prod['id'], 'title': rc_prod['title'],
        #         'description': rc_prod['description'],
        #         'rating': rc_prod['rating'],
        #         'stockrecords': rc_prod['stockrecords'], 'images': rc_prod['images'],
        #         'price': rc_prod['price'], 'availability': rc_prod['availability'],
        #         })
        return Response({'url': ser.data['url'], 'id': ser.data['id'], 'title': ser.data['title'],
                         'description': ser.data['description'], 'reviews': ser.data['reviews'],
                         'date_created': ser.data['date_created'], 'date_updated': ser.data['date_updated'],
                         'attributes': ser.data['attributes'], 'product_class': ser.data['product_class'],
                         'rating': ser.data['rating'],
                         'stockrecords': ser.data['stockrecords'], 'images': ser.data['images'],
                         'price': ser.data['price'], 'availability': ser.data['availability'],
                         'options': ser.data['options'],
                         'ancestors': cat_ops.fetch_ancestors_and_self(prodcat, request),
                         'recommended': recommended_products, 'parent': ser.data['parent']})


class ProductListCategory(generics.ListAPIView):
    serializer_class = ProductSerializer
    model = serializer_class.Meta.model
    paginate_by = 100

    def get_queryset(self):
        category_id = self.kwargs['pk']
        queryset = self.model.objects.filter(categories__id=category_id)
        return queryset


class ProductListSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    model = serializer_class.Meta.model
    paginate_by = 100

    def get_queryset(self):
        pattern = self.kwargs['pattern']

        queryset = self.model.objects.filter(slug__icontains=pattern)
        return queryset


class ProductTaxPrice(generics.RetrieveAPIView):
    def get(self, request, pk=None, format=None):
        product = Product.objects.get(id=pk)
        strategy = Selector().strategy(request=request, user=request.user)
        ser = PriceTaxSerializer(strategy.fetch_for_product(product).price, context={'request': request})
        return Response(ser.data)


class ReviewProduct(APIView):
    authentication_classes = []
    """

    """

    serializer_class = serializers.ProductReviewSerializer

    def post(self, request, pk=None, format=None):

        product = get_object_or_404(Product, pk=request.data['product'])
        score = request.data['score']
        title = request.data['title']
        body = request.data['body']
        token = request.data['token']
        tokken = Token
        user = None
        try:
            tokken = Token.objects.get(key=token)
            user = tokken.user
        except tokken.DoesNotExist:
            user = request.user
        if not product.is_review_permitted(user):
            if product.has_review_by(user):
                return Response(
                    {'response': '403', 'message': 'You already reviewed this product'},
                    status=status.HTTP_403_FORBIDDEN)
            else:
                return Response(
                    {'response': '401', 'message': "You can't leave a review for this product."},
                    status=status.HTTP_401_UNAUTHORIZED)
            return Response(
                {'response': '403', 'message': 'You cannot review this product'},
                status=status.HTTP_403_FORBIDDEN)

        pr = ProductReview.objects.create(product=product, score=score, title=title, body=body, status=0)
        if not user.is_anonymous():
            pr.user = user
        pr.save()
        product.update_rating()
        return Response(
            {'response': '200', 'message': 'Review added successfully to product'},
            status=status.HTTP_200_OK)














