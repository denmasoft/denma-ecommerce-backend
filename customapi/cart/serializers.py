from __future__ import unicode_literals
import warnings

from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import gettext as _
from oscar.core import prices
from oscar.core.loading import get_class, get_model
from rest_framework import serializers, exceptions
from rest_framework import serializers
from decimal import Decimal as D
from oscarapi.utils import (
    OscarHyperlinkedModelSerializer,
    OscarModelSerializer,
    overridable
)
from oscarapi.serializers.fields import TaxIncludedDecimalField
from oscarapi.basket import operations
from oscar.apps.catalogue.models import Product
#from oscar.apps.basket.models import Line
from oscar.core.loading import get_model
from decimal import Decimal
from oscarapi.serializers import (
    VoucherSerializer,
    OfferDiscountSerializer
)
from oscarapi.basket.operations import (
    assign_basket_strategy,
)
from oscarapi.utils import (
    overridable,
    OscarModelSerializer,
    OscarHyperlinkedModelSerializer,
    DrillDownHyperlinkedIdentityField
)
from customapi.basket.models import Basket
from customapi.basket.models import Line
from customapi.products.serializers import ProductSerializer,UserSerializer, StockRecordSerializer
from customapi.wishlist.serializers import WishListLineSerializer
from customapi.partner.strategy import Selector
LineAttribute = get_model('basket', 'LineAttribute')
Option = get_model('catalogue', 'Option')
ShippingAddress = get_model('order', 'ShippingAddress')
Order = get_model('order', 'Order')
Country = get_model('address', 'Country')
BillingAddress = get_model('order', 'BillingAddress')
OrderPlacementMixin = get_class('checkout.mixins', 'OrderPlacementMixin')
OrderTotalCalculator = get_class('checkout.calculators',
                               'OrderTotalCalculator')
Repository = get_class('shipping.repository', 'Repository')


class CartCustomSerializer(serializers.ModelSerializer):
    # url = serializers.HyperlinkedRelatedField(view_name='product-detail', queryset=Product.objects, required=True)

    class Meta:
        model = Line
        fields = ['product', 'quantity']



class CartOptionValueSerializer(serializers.Serializer):
    option = serializers.HyperlinkedRelatedField(
        view_name='option-detail', queryset=Option.objects)
    value = serializers.CharField()


class CartRemoveProductSerializer(serializers.ModelSerializer):

    id = serializers.PrimaryKeyRelatedField(queryset=Product.objects, required=True)
    options = CartOptionValueSerializer(many=True, required=False)
    quantity = serializers.IntegerField(required=True)

    class Meta:
        model = Line
        fields = ['quantity', 'id', 'options']


class CartAddProductSerializer(serializers.Serializer):
    """
    Serializes and validates an add to basket request.
    """
    quantity = serializers.IntegerField(required=True)
    id = serializers.PrimaryKeyRelatedField(queryset=Product.objects, required=True)
    options = CartOptionValueSerializer(many=True, required=False)

    class Meta:
        model = Line
        fields = ['quantity', 'id', 'options']


class ShippingAddressSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = '__all__'


class BillingAddressSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = BillingAddress
        fields = '__all__'


class InlineShippingAddressSerializer(OscarModelSerializer):
    country = serializers.HyperlinkedRelatedField(
        view_name='country-detail', queryset=Country.objects)

    class Meta:
        model = ShippingAddress
        fields = '__all__'


class InlineBillingAddressSerializer(OscarModelSerializer):
    country = serializers.HyperlinkedRelatedField(
        view_name='country-detail', queryset=Country.objects)

    class Meta:
        model = BillingAddress
        fields = '__all__'


class OrderOfferDiscountSerializer(OfferDiscountSerializer):
    name = serializers.CharField(source='offer_name')
    amount = serializers.DecimalField(decimal_places=2, max_digits=12)


class OrderVoucherOfferSerializer(OrderOfferDiscountSerializer):
    voucher = VoucherSerializer(required=False)


class CustomOrderSerializer(OscarHyperlinkedModelSerializer):
    """
    The order serializer tries to have the same kind of structure as the
    basket. That way the same kind of logic can be used to display the order
    as the basket in the checkout process.
    """
    owner = serializers.HyperlinkedRelatedField(
        view_name='user-detail', read_only=True, source='user')
    lines = serializers.HyperlinkedIdentityField(
        view_name='order-lines-list')
    shipping_address = InlineShippingAddressSerializer(
        many=False, required=False)
    billing_address = InlineBillingAddressSerializer(
        many=False, required=False)

    payment_url = serializers.SerializerMethodField()
    offer_discounts = serializers.SerializerMethodField()
    voucher_discounts = serializers.SerializerMethodField()

    def get_offer_discounts(self, obj):
        qs = obj.basket_discounts.filter(offer_id__isnull=False)
        return OrderOfferDiscountSerializer(qs, many=True).data

    def get_voucher_discounts(self, obj):
        qs = obj.basket_discounts.filter(voucher_id__isnull=False)
        return OrderVoucherOfferSerializer(qs, many=True).data

    def get_payment_url(self, obj):
        request = self.context['request']
        payment_type = request.data["payment_method"]
        try:
            return reverse(payment_type+'-payment', args=(obj.pk,))
        except NoReverseMatch:
            msg = "You need to implement a payment provider " \
                "which redirects to and sets up the " \
                "callbacks."
            warnings.warn(msg)
            return msg

    class Meta:
        model = Order
        fields = overridable('OSCARAPI_ORDER_FIELD', default=(
            'number', 'basket', 'url', 'lines',
            'owner', 'billing_address', 'currency', 'total_incl_tax',
            'total_excl_tax', 'shipping_incl_tax', 'shipping_excl_tax',
            'shipping_address', 'shipping_method', 'shipping_code', 'status',
            'guest_email', 'date_placed', 'payment_url', 'offer_discounts',
            'voucher_discounts')
        )


class PriceSerializer(serializers.Serializer):
    currency = serializers.CharField(
        max_length=12, default=settings.OSCAR_DEFAULT_CURRENCY, required=False)
    excl_tax = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=True)
    incl_tax = TaxIncludedDecimalField(
        excl_tax_field='excl_tax',
        decimal_places=2, max_digits=12, required=False)
    tax = TaxIncludedDecimalField(
        excl_tax_value='0.00',
        decimal_places=2, max_digits=12, required=False)


class CustomCheckoutSerializer(serializers.Serializer, OrderPlacementMixin):
    basket = serializers.HyperlinkedRelatedField(
        view_name='basket-detail', queryset=Basket.objects)
    guest_email = serializers.EmailField(allow_blank=True, required=False)
    total = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=False)
    shipping_method_code = serializers.CharField(
        max_length=128, required=False)
    shipping_charge = PriceSerializer(many=False, required=False)
    shipping_address = ShippingAddressSerializer(many=False, required=False)
    billing_address = BillingAddressSerializer(many=False, required=False)

    def get_initial_order_status(self, basket):
        return overridable('OSCARAPI_INITIAL_ORDER_STATUS', default='new')

    def validate(self, attrs):
        request = self.context['request']

        if request.user.is_anonymous():
            if not settings.OSCAR_ALLOW_ANON_CHECKOUT:
                message = _('Anonymous checkout forbidden')
                raise serializers.ValidationError(message)

            if not attrs.get('guest_email'):
                # Always require the guest email field if the user is anonymous
                message = _('Guest email is required for anonymous checkouts')
                raise serializers.ValidationError(message)
        else:
            if 'guest_email' in attrs:
                # Don't store guest_email field if the user is authenticated
                del attrs['guest_email']

        basket = attrs.get('basket')
        basket = assign_basket_strategy(basket, request)
        if basket.num_items <= 0:
            message = _('Cannot checkout with empty basket')
            raise serializers.ValidationError(message)

        shipping_method = self._shipping_method(
            request, basket,
            attrs.get('shipping_method_code'),
            attrs.get('shipping_address')
        )
        shipping_charge = shipping_method.calculate(basket)
        posted_shipping_charge = attrs.get('shipping_charge')

        if posted_shipping_charge is not None:
            posted_shipping_charge = prices.Price(**posted_shipping_charge)
            # test submitted data.
            if not posted_shipping_charge == shipping_charge:
                message = _('Shipping price incorrect %s != %s' % (
                    posted_shipping_charge, shipping_charge
                ))
                raise serializers.ValidationError(message)

        posted_total = attrs.get('total')
        total = OrderTotalCalculator().calculate(basket, shipping_charge)
        if posted_total is not None:
            if posted_total != total.incl_tax:
                message = _('Total incorrect %s != %s' % (
                    posted_total,
                    total.incl_tax
                ))
                raise serializers.ValidationError(message)

        # update attrs with validated data.
        attrs['total'] = total
        attrs['shipping_method'] = shipping_method
        attrs['shipping_charge'] = shipping_charge
        attrs['basket'] = basket
        return attrs

    def create(self, validated_data):
        try:
            basket = validated_data.get('basket')
            order_number = self.generate_order_number(basket)
            request = self.context['request']

            shipping_address = ShippingAddress(
                **validated_data['shipping_address'])

            if 'billing_address' in validated_data:
                billing_address = BillingAddress(
                    **validated_data['billing_address'])
            else:
                billing_address = None

            return self.place_order(
                order_number=order_number,
                user=request.user,
                basket=basket,
                shipping_address=shipping_address,
                shipping_method=validated_data.get('shipping_method'),
                shipping_charge=validated_data.get('shipping_charge'),
                billing_address=billing_address,
                order_total=validated_data.get('total'),
                guest_email=validated_data.get('guest_email') or ''
            )
        except ValueError as e:
            raise exceptions.NotAcceptable(e.message)

    def _shipping_method(self, request, basket,
                         shipping_method_code, shipping_address):
        repo = Repository()

        default = repo.get_default_shipping_method(
            basket=basket,
            user=request.user,
            request=request,
            shipping_addr=shipping_address
        )

        if shipping_method_code is not None:
            methods = repo.get_shipping_methods(
                basket=basket,
                user=request.user,
                request=request,
                shipping_addr=shipping_address
            )

            find_method = (
                s for s in methods if s.code == shipping_method_code)
            shipping_method = next(find_method, default)
            return shipping_method

        return default


class OfferDiscountSerializer(serializers.Serializer):
    description = serializers.CharField()
    name = serializers.CharField()
    amount = serializers.DecimalField(
        decimal_places=2, max_digits=12, source='discount')


class VoucherDiscountSerializer(OfferDiscountSerializer):
    voucher = VoucherSerializer(required=False)


class PriceTaxSerializer(serializers.Serializer):
    currency = serializers.CharField(
        max_length=12, default=settings.OSCAR_DEFAULT_CURRENCY, required=False)
    excl_tax = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=True)
    incl_tax = TaxIncludedDecimalField(
        excl_tax_field='excl_tax',
        decimal_places=2, max_digits=12, required=False)
    tax = TaxIncludedDecimalField(
        excl_tax_value=settings.TAX,
        decimal_places=2, max_digits=12, required=False)


class OptionSerializer(OscarHyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'name']


class CustomLineAttributeSerializer(OscarHyperlinkedModelSerializer):
    option = OptionSerializer(required=True)

    class Meta:
        model = LineAttribute
        fields = ['url', 'option', 'value']


class LineAttributeSerializer(OscarHyperlinkedModelSerializer):
    option = OptionSerializer(required=True)

    class Meta:
        model = LineAttribute
        fields = ['url', 'option', 'value']


class CartLineSerializer(serializers.HyperlinkedModelSerializer):

    product = ProductSerializer(required=True)
    attributes = LineAttributeSerializer(
        many=True,
        required=False,
        read_only=True)

    class Meta:
        model = Line
        fields = ['product', 'id', 'quantity', 'price_currency', 'price_excl_tax', 'price_incl_tax', 'attributes']


class CustomBasketSerializer(serializers.HyperlinkedModelSerializer):
    lines = CartLineSerializer(many=True, required=True)
    offer_discounts = OfferDiscountSerializer(many=True, required=False)
    total_excl_tax = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=False)
    total_excl_tax_excl_discounts = serializers.DecimalField(
        decimal_places=2, max_digits=12, required=False)
    total_incl_tax = TaxIncludedDecimalField(
        excl_tax_field='total_excl_tax', decimal_places=2,
        max_digits=12, required=False)
    total_incl_tax_excl_discounts = TaxIncludedDecimalField(
        excl_tax_field='total_excl_tax_excl_discounts', decimal_places=2,
        max_digits=12, required=False)
    total_tax = TaxIncludedDecimalField(
        excl_tax_value=Decimal('0.00'), decimal_places=2,
        max_digits=12, required=False)
    currency = serializers.CharField(required=False)
    voucher_discounts = VoucherDiscountSerializer(many=True, required=False)

    class Meta:
        model = Basket
        fields = overridable('OSCARAPI_BASKET_FIELDS', default=(
            'id', 'owner', 'status', 'lines',
            'url', 'total_excl_tax',
            'total_excl_tax_excl_discounts', 'total_incl_tax',
            'total_incl_tax_excl_discounts', 'total_tax', 'currency',
            'voucher_discounts', 'offer_discounts', 'is_tax_known'))

    def get_validation_exclusions(self, instance=None):
        """
        This is needed because oscar declared the owner field as ``null=True``,
        but ``blank=False``. That means the validator will claim you can not
        leave this value set to None.
        """
        return super(CustomBasketSerializer, self).get_validation_exclusions(
            instance) + ['owner']





class CustomLineSerializer(serializers.HyperlinkedModelSerializer):
    """
    This serializer just shows fields stored in the database for this line.
    """

    attributes = CustomLineAttributeSerializer(
        many=True,
        required=False,
        read_only=True)

    class Meta:
        model = Line
        fields = '__all__'


class CustomBasketLineSerializer(OscarHyperlinkedModelSerializer):
    """
    This serializer computes the prices of this line by using the basket
    strategy.
    """
    url = DrillDownHyperlinkedIdentityField(
        view_name='basket-line-detail',
        extra_url_kwargs={'basket_pk': 'basket.id'})
    product = ProductSerializer(required=True)
    stockrecord = StockRecordSerializer(required=False)
    attributes = CustomLineAttributeSerializer(
        many=True, fields=('url', 'option', 'value'),
        required=False, read_only=True)
    price_excl_tax = serializers.DecimalField(
        decimal_places=2, max_digits=12,
        source='line_price_excl_tax_incl_discounts')
    price_incl_tax = TaxIncludedDecimalField(
        decimal_places=2, max_digits=12,
        excl_tax_field='line_price_excl_tax_incl_discounts',
        source='line_price_incl_tax_incl_discounts')
    price_incl_tax_excl_discounts = TaxIncludedDecimalField(
        decimal_places=2, max_digits=12,
        excl_tax_field='line_price_excl_tax',
        source='line_price_incl_tax')
    price_excl_tax_excl_discounts = serializers.DecimalField(
        decimal_places=2, max_digits=12,
        source='line_price_excl_tax')
    warning = serializers.CharField(
        read_only=True, required=False, source='get_warning')

    @property
    def basket_pk(self):
        return self.kwargs.get('basket_pk')

    class Meta:
        model = Line
        fields = overridable('OSCARAPI_BASKETLINE_FIELDS', default=(
            'url', 'product', 'quantity', 'attributes', 'price_currency',
            'price_excl_tax', 'price_incl_tax',
            'price_incl_tax_excl_discounts', 'price_excl_tax_excl_discounts',
            'is_tax_known', 'warning', 'basket', 'stockrecord', 'date_created'
        ))

    def to_representation(self, obj):
        # This override is needed to reflect offer discounts or strategy
        # related prices immediately in the response
        operations.assign_basket_strategy(obj.basket, self.context['request'])

        # Oscar stores the calculated discount in line._discount_incl_tax or
        # line._discount_excl_tax when offers are applied. So by just
        # retrieving the line from the db you will loose this values, that's
        # why we need to get the line from the in-memory resultset here
        lines = (x for x in obj.basket.all_lines() if x.id == obj.id)
        line = next(lines, None)

        return super(CustomBasketLineSerializer, self).to_representation(line)

class UserOrderSerializer(OscarHyperlinkedModelSerializer):    
    owner = serializers.HyperlinkedRelatedField(
        view_name='user-detail', read_only=True, source='user')   

    class Meta:
        model = Order
        fields = overridable('OSCARAPI_ORDER_FIELD', default=(
            'number', 'owner','status')
        )