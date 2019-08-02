# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers
from oscar.core.loading import get_model

ProductReview = get_model('reviews', 'productreview')


#Default serializer for Reviews
class ProductReviewSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ProductReview







