# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import generics
from oscar.core.loading import get_model
import serializers

SourceType = get_model('payment', 'SourceType')


class SourceTypeList(generics.ListAPIView):
    serializer_class = serializers.SourceTypeSerializer
    queryset = SourceType.objects.all()

class SourceTypeDetail(generics.RetrieveAPIView):
    serializer_class = serializers.SourceTypeSerializer
    model = SourceType