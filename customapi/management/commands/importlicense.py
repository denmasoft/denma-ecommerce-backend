from __future__ import unicode_literals
import os
from django.core.management.base import BaseCommand, CommandError
from oscar.core.loading import get_model, get_class
from django.db.models import Q
from customapi.basket.models import Basket
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')
Line = get_model('basket', 'Line')
StockRecord = get_model('partner', 'StockRecord')
ProductReview = get_model('reviews', 'ProductReview')
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (
    DeleteView, DetailView, FormView, ListView, UpdateView)
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django_tables2 import SingleTableView

from oscar.apps.customer.utils import normalise_email
from oscar.core.compat import get_user_model
from oscar.core.loading import get_class, get_classes, get_model
from oscar.views.generic import BulkEditMixin
from customapi.license.models import License
from customapi.user.models import WholeSale
import csv
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = 'Importing licenses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv', dest='csv', required=True,
            help='the csv to process',
        )

    def handle(self, *args, **options):
        csvdir = os.path.join(settings.BASE_DIR, 'licenses/')
        my_uploaded_file = csvdir+options['csv']
        count = 0
        with open(my_uploaded_file, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] != 'Board':
                    try:
                        License.objects.get(Q(license_number=row[12]) & Q(alternate_license_number=row[19]))
                    except ObjectDoesNotExist:
                        lic = License.objects.create(
                            board=row[0],
                            occupation=str(row[1]).decode('unicode_escape'),
                            licensee=str(row[2]).decode('unicode_escape'),
                            doing_business_as=str(row[3]).decode('unicode_escape'),
                            cls=str(row[4]).decode('unicode_escape'),
                            line1=str(row[5]).decode('unicode_escape'),
                            line2=str(row[6]).decode('unicode_escape'),
                            line3=str(row[7]).decode('unicode_escape'),
                            city=str(row[8]).decode('unicode_escape'),
                            state=row[9],
                            zipcode=row[10],
                            county=row[11],
                            license_number=row[12],
                            primary_status=str(row[13]).decode('unicode_escape'),
                            secondary_status=str(row[14]).decode('unicode_escape'),
                            date_licensed=row[15],
                            effective_date=row[16],
                            expiration_date=row[17],
                            military=str(row[18]).decode('unicode_escape'),
                            alternate_license_number=row[19],
                        )
                        lic.save()
                        count = count + 1
        self.stdout.write(self.style.SUCCESS(str(count) + 'licenses successfully added.'))