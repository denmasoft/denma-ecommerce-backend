# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-07 03:36
from __future__ import unicode_literals

from django.db import migrations, models
import oscar.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='company',
            field=models.CharField(blank=True, max_length=255, verbose_name='Company'),
        ),
        migrations.AddField(
            model_name='useraddress',
            name='fax',
            field=oscar.models.fields.PhoneNumberField(blank=True, help_text='In case we need to send your order.', verbose_name='Fax'),
        ),
    ]