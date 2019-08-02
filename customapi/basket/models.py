from oscar.apps.basket.abstract_models import (AbstractBasket,AbstractLine)
from django.db import models
from django.utils.translation import ugettext_lazy as _
from oscar.apps.catalogue.models import Option
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from decimal import Decimal as D
from customapi.partner.strategy import Selector


class Basket(AbstractBasket):

    def add_product(self, product, quantity=1, options=None):
        """
        Add a product to the basket

        'stock_info' is the price and availability data returned from
        a partner strategy class.

        The 'options' list should contains dicts with keys 'option' and 'value'
        which link the relevant product.Option model and string value
        respectively.

        Returns (line, created).
          line: the matching basket line
          created: whether the line was created or updated

        """
        if options is None:
            options = []
        if not self.id:
            self.save()

        # Ensure that all lines are the same currency
        price_currency = self.currency
        stock_info = self.strategy.fetch_for_product(product)
        if price_currency and stock_info.price.currency != price_currency:
            raise ValueError((
                "Basket lines must all have the same currency. Proposed "
                "line has currency %s, while basket has currency %s")
                % (stock_info.price.currency, price_currency))

        if stock_info.stockrecord is None:
            raise ValueError((
                "Basket lines must all have stock records. Strategy hasn't "
                "found any stock record for product %s") % product)

        # Line reference is used to distinguish between variations of the same
        # product (eg T-shirts with different personalisations)
        line_ref = self._create_line_reference(
            product, stock_info.stockrecord, options)

        # Determine price to store (if one exists).  It is only stored for
        # audit and sometimes caching.
        defaults = {
            'quantity': quantity,
            'price_excl_tax': stock_info.price.excl_tax,
            'price_currency': stock_info.price.currency,
        }
        if stock_info.price.is_tax_known:
            defaults['price_incl_tax'] = stock_info.price.incl_tax

        line, created = self.lines.get_or_create(
            line_reference=line_ref,
            product=product,
            stockrecord=stock_info.stockrecord,
            defaults=defaults)
        if created:
            for option_dict in options:
                line.attributes.create(option=option_dict['option'], value=option_dict['value'])
        else:
            line.quantity = max(0, int(line.quantity) + int(quantity))
            line.save()
        self.reset_offer_applications()

        # Returning the line is useful when overriding this method.
        return line, created
    add_product.alters_data = True
    add = add_product

    def remove(self, product, quantity=0, options=None):
        """
        Remove a product from this cart
        """
        if options is None:
            options = []
        price_currency = self.currency
        stock_info = self.strategy.fetch_for_product(product)
        if price_currency and stock_info.price.currency != price_currency:
            raise ValueError((
                                 "Basket lines must all have the same currency. Proposed "
                                 "line has currency %s, while basket has currency %s")
                             % (stock_info.price.currency, price_currency))

        if stock_info.stockrecord is None:
            raise ValueError((
                                 "Basket lines must all have stock records. Strategy hasn't "
                                 "found any stock record for product %s") % product)

        # Line reference is used to distinguish between variations of the same
        # product (eg T-shirts with different personalisations)
        line_ref = self._create_line_reference(
            product, stock_info.stockrecord, options)

        # Determine price to store (if one exists).  It is only stored for
        # audit and sometimes caching.
        defaults = {
            'quantity': quantity,
            'price_excl_tax': stock_info.price.excl_tax,
            'price_currency': stock_info.price.currency,
        }
        if stock_info.price.is_tax_known:
            defaults['price_incl_tax'] = stock_info.price.incl_tax

        # line = self.lines.get(line_reference=line_ref)
        # line.delete()
        ref = self._create_line_reference(product, stock_info.stockrecord, options)
        line = self.lines.get(line_reference=ref)
        if line:
            if quantity is not 0:
                line.quantity = max(0, int(line.quantity) - int(quantity))
                line.save()
                if line.quantity is 0:
                    line.delete()
            else:
                line.delete()


class Line(AbstractLine):

    def discount(self, discount_value, affected_quantity, incl_tax=True):
        """
        Apply a discount to this line
        """
        if incl_tax:
            if self._discount_excl_tax > 0:
                raise RuntimeError(
                    "Attempting to discount the tax-inclusive price of a line "
                    "when tax-exclusive discounts are already applied")
            self._discount_incl_tax += discount_value
        else:
            if self._discount_incl_tax > 0:
                raise RuntimeError(
                    "Attempting to discount the tax-exclusive price of a line "
                    "when tax-inclusive discounts are already applied")
            self._discount_excl_tax += discount_value
        self._affected_quantity += int(affected_quantity)

    def consume(self, quantity):
        """
        Mark all or part of the line as 'consumed'

        Consumed items are no longer available to be used in offers.
        """
        if quantity > self.quantity - self._affected_quantity:
            inc = self.quantity - self._affected_quantity
        else:
            inc = quantity
        self._affected_quantity += int(inc)

    def get_price_breakdown(self):
        """
        Return a breakdown of line prices after discounts have been applied.

        Returns a list of (unit_price_incl_tax, unit_price_excl_tax, quantity)
        tuples.
        """
        if not self.is_tax_known:
            raise RuntimeError("A price breakdown can only be determined "
                               "when taxes are known")
        prices = []
        if not self.discount_value:
            prices.append((self.unit_price_incl_tax, self.unit_price_excl_tax,
                           self.quantity))
        else:
            # Need to split the discount among the affected quantity
            # of products.
            item_incl_tax_discount = (
                self.discount_value / int(self._affected_quantity))
            item_excl_tax_discount = item_incl_tax_discount * self._tax_ratio
            item_excl_tax_discount = item_excl_tax_discount.quantize(D('0.01'))
            prices.append((self.unit_price_incl_tax - item_incl_tax_discount,
                           self.unit_price_excl_tax - item_excl_tax_discount,
                           self._affected_quantity))
            if self.quantity_without_discount:
                prices.append((self.unit_price_incl_tax,
                               self.unit_price_excl_tax,
                               self.quantity_without_discount))
        return prices

    # =======
    # Helpers
    # =======

    @property
    def _tax_ratio(self):
        if not self.unit_price_incl_tax:
            return 0
        return self.unit_price_excl_tax / self.unit_price_incl_tax

    # ==========
    # Properties
    # ==========

    @property
    def has_discount(self):
        return self.quantity > self.quantity_without_discount

    @property
    def quantity_with_discount(self):
        return self._affected_quantity

    @property
    def quantity_without_discount(self):
        return int(self.quantity - self._affected_quantity)

    @property
    def is_available_for_discount(self):
        return self.quantity_without_discount > 0

    @property
    def discount_value(self):
        # Only one of the incl- and excl- discounts should be non-zero
        return max(self._discount_incl_tax, self._discount_excl_tax)

    @property
    def purchase_info(self):
        """
        Return the stock/price info
        """
        if not hasattr(self, '_info'):
            # Cache the PurchaseInfo instance.
            strategy = Selector().strategy()
            self._info = strategy.fetch_for_line(self, self.stockrecord)
        return self._info

    @property
    def is_tax_known(self):
        return self.purchase_info.price.is_tax_known

    @property
    def unit_effective_price(self):
        """
        The price to use for offer calculations
        """
        return self.purchase_info.price.effective_price

    @property
    def unit_price_excl_tax(self):
        return self.purchase_info.price.excl_tax

    @property
    def unit_price_incl_tax(self):
        return self.purchase_info.price.incl_tax

    @property
    def unit_tax(self):
        return self.purchase_info.price.tax

    @property
    def line_price_excl_tax(self):
        return self.quantity * self.unit_price_excl_tax

    @property
    def line_price_excl_tax_incl_discounts(self):
        if self._discount_excl_tax:
            return self.line_price_excl_tax - self._discount_excl_tax
        if self._discount_incl_tax:
            # This is a tricky situation.  We know the discount as calculated
            # against tax inclusive prices but we need to guess how much of the
            # discount applies to tax-exclusive prices.  We do this by
            # assuming a linear tax and scaling down the original discount.
            return self.line_price_excl_tax \
                   - self._tax_ratio * self._discount_incl_tax
        return self.line_price_excl_tax

    @property
    def line_price_incl_tax_incl_discounts(self):
        # We use whichever discount value is set.  If the discount value was
        # calculated against the tax-exclusive prices, then the line price
        # including tax
        return self.line_price_incl_tax - self.discount_value

    @property
    def line_tax(self):
        return self.quantity * self.unit_tax

    @property
    def line_price_incl_tax(self):
        return self.quantity * self.unit_price_incl_tax
from oscar.apps.basket.models import *