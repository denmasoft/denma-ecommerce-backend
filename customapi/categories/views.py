# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import generics
from django.shortcuts import get_object_or_404
from oscar.core.loading import get_model
import serializers
from .serializers import (CategorySerializer)
from customapi.categories.mixin import AllowCORSMixin
from rest_framework.response import Response
from oscar.apps.catalogue.models import Product
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal as D
from django.db.models import Max
from django.db.models import Q
from customapi.products.serializers import (ProductLinkSerializer, ProductSerializer, ProductImageSerializer,
                                            PriceTaxSerializer, OptionsSerializer,ProdSerializer)
from rest_framework.authentication import (TokenAuthentication, SessionAuthentication)
from customapi.categories import operations as cat_ops

Category = get_model('catalogue', 'Category')
ProductCategory = get_model('catalogue', 'ProductCategory')


class CategoryList(generics.ListAPIView):

    def get(self, request, pk=None, format=None):
        categories = Category.objects.filter(depth=1)
        result = cat_ops.process_category_list(categories, request)
        response = Response(result)
        return response


class ChildrenByCategory(generics.ListAPIView):

    def get(self, request, pk=None, format=None):
        category = get_object_or_404(Category, pk=pk)
        result = cat_ops.process_category_list(category.get_children(), request)
        response = Response(result)
        return response


class ByCategory(generics.ListAPIView):


    # def get(self, request, pk=None, format=None):
     #   category = get_object_or_404(Category, pk=pk)
     #   hair_color = self.process_hair_colors(category, request)
     #   if category.name in "Hair Color" or hair_color is True and category.is_leaf() is False:
     #       leafs = self.process_leafs(category.get_descendants(), request)
     #       response = Response({'id': category.id, 'name': category.name, 'leafs': leafs})
     #       return response
     #   children = self.process_tree(category.get_children(), request)
     #   products = self.process_products(category, request)
     #   response = Response(
     #       {'id': category.id, 'name': category.name, 'hair_color': self.process_hair_colors(category, request),
     #        'children': children, 'products': products})
     #   return response

    def get(self, request, pk=None, format=None):
        category = get_object_or_404(Category, pk=pk)
        hair_color = cat_ops.process_hair_colors(category, request)
        parent = cat_ops.process_parent(category.get_parent(), request)
        count = Product.objects.filter(categories__id=category.id).count()
        if category.name in "Hair Color" or parent in "Hair Color":
            leafs = cat_ops.process_tree(category.get_children(), request)
            response = Response({'id': category.id, 'name': category.name, 'leafs': leafs, "ancestors": cat_ops.fetch_ancestors(category, request)})
            return response
        #if hair_color is True:
         #   variants = cat_ops.process_variants(category.get_descendants(), request)
         #   response = Response({'id': category.id, 'name': category.name, 'hair_color': hair_color, 'products': variants,"ancestors": cat_ops.fetch_ancestors(category, request)})
         #   return response

        if hair_color is True and count is 0:
            variants = cat_ops.process_variants(category.get_descendants(), request)
            response = Response({'id': category.id, 'name': category.name, 'hair_color': hair_color, 'products': variants, "ancestors": cat_ops.fetch_ancestors(category, request)})
            return response
        else:
            children = cat_ops.process_tree(category.get_children(), request)
            products = cat_ops.process_products(category, request)
            response = Response(
                {'id': category.id, 'name': category.name, 'hair_color': cat_ops.process_hair_colors(category, request),
                    'children': children, 'products': products, "ancestors": cat_ops.fetch_ancestors(category, request)})
            return response


class LoadMoreProducts(generics.ListAPIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        category = request.data['category']
        category = get_object_or_404(Category, pk=category)
        products = cat_ops.process_products(category, request)
        response = Response(products)
        return response


class SearchProducts(generics.ListAPIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        parent = get_object_or_404(Category, pk=request.data['id'])
        offset = 0
        limit = 12
        if 'limit' in request.data:
            limit = request.data['limit']
        if 'offset' in request.data:
            offset = request.data['offset']
        q_objects = Q()
        products = None
        if 'category' in request.data:
            category = request.data['category']
            if category != 'null':
                cc = get_object_or_404(Category, pk=category)
                if cc.name == 'Hair Color' or cat_ops.process_hair_colors(cc, request):
                    ccats = []
                    for cat in cc.get_descendants():
                        ccats.append(cat.id)
                    q_objects.add(Q(categories__id__in=ccats), Q.AND)
                else:
                    q_objects.add(Q(categories__id=category), Q.AND)
        else:
            cats = []
            for cat in parent.get_children():
                cats.append(cat.id)
            q_objects.add(Q(categories__id__in=cats), Q.AND)
        if 'period' in request.data:
            period = request.data['period']
            if period != 'null':
                period_date = timezone.now() - timedelta(days=int(period))
                q_objects.add(Q(date_created__gte=period_date), Q.AND)
        if 'min_price' in request.data and 'max_price' in request.data:
            max_price = request.data['max_price']
            min_price = request.data['min_price']
            min_price = D(min_price)
            max_price = D(max_price)
            if max_price == 0:
                if 'license' in request.data:
                    max_price = Product.objects.aggregate(Max('stockrecords__cost_price'))['stockrecords__cost_price__max']
                else:
                    max_price = Product.objects.aggregate(Max('stockrecords__price_excl_tax'))['stockrecords__price_excl_tax__max']
            if 'license' in request.data:
                q_objects.add(Q(stockrecords__cost_price__range=(min_price, max_price)), Q.AND)
            else:
                q_objects.add(Q(stockrecords__price_excl_tax__range=(min_price, max_price)), Q.AND)
        products = Product.objects.filter(q_objects)[offset:limit]
        response = Response({'products': cat_ops.process_category_products(products, request)})
        return response


class GenerateSlugs(generics.ListAPIView):
    def get(self, request):
        slugs = []
        for category in Category.objects.all():
            slug = '<url><loc>https://southbeautysupply.com/category/' + category.slug + '-' + str(
                category.id) + '</loc>'
            slug += '<lastmod>2017-07-31T21:46:35+00:00</lastmod>'
            slug += '<changefreq>daily</changefreq>'
            slug += '<priority>1.00</priority>'
            slug += '</url>'
            slugs.append(slug)
        for product in Product.objects.all():
            slug = '<url><loc>https://southbeautysupply.com/product/' + product.slug + '-' + str(
                product.id) + '</loc>'
            slug += '<lastmod>2017-07-31T21:46:35+00:00</lastmod>'
            slug += '<changefreq>daily</changefreq>'
            slug += '<priority>1.00</priority>'
            slug += '</url>'
            slugs.append(slug)
        response = Response(slugs)
        return response