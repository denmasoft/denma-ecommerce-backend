# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-07 14:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customapi', '0003_auto_20170707_1359'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='creditcard',
            table='credit_card',
        ),
    ]