# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import generics
from django.shortcuts import get_object_or_404
from oscar.core.loading import get_model
import serializers
from .serializers import (LicenseSerializer)
from rest_framework.response import Response
from customapi.license.models import License


class WholesaleLicense(generics.ListAPIView):
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
