from django.core.management.base import BaseCommand, CommandError
from __future__ import unicode_literals
from oscar.core.loading import get_model, get_class
from django.db.models import Q
from customapi.basket.models import Basket
Product = get_model('catalogue', 'Product')
Order = get_model('order', 'Order')
Line = get_model('basket', 'Line')
StockRecord = get_model('partner', 'StockRecord')
ProductReview = get_model('reviews', 'ProductReview')

class Command(BaseCommand):
    help = 'Resetting orders'

    def handle(self, *args, **options):
        reviews = ProductReview.objects.all()
        for review in reviews:
            review.delete()
        self.stdout.write(self.style.SUCCESS('Dashboard cleaned.'))