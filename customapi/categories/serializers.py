# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers

from oscarapi.utils import (OscarModelSerializer)
from oscar.core.loading import get_model

Category = get_model('catalogue', 'Category')


class CategorySerializer(OscarModelSerializer):
    """
    Product category serializer
    """

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image']