# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from rest_framework import serializers

from oscarapi.utils import (OscarModelSerializer)
from oscar.core.loading import get_model
from customapi.license.models import License


class LicenseSerializer(OscarModelSerializer):
    """
    
    """
    class Meta:
        model = License
        fields = '__all__'
