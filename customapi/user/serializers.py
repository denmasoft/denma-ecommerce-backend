from django.contrib.auth.models import User
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import *
from django.conf import settings
from django.template.loader import render_to_string
from smtplib import SMTP_SSL as SMTP
from rest_framework import serializers
from customapi.address.models import UserAddress
from customapi.user.models import Newsletter
from customapi.user.models import WholeSale
from oscar.apps.address.models import Country
from rest_framework import status
from rest_framework.response import Response
from django.core.mail import send_mail
from customapi.parameters import *
from oscarapi.utils import overridable


def field_length(fieldname):
    field = next(
        field for field in User._meta.fields if field.name == fieldname)
    return field.max_length


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('iso_3166_1_a2', 'iso_3166_1_a3', 'iso_3166_1_numeric', 'printable_name', 'name', 'display_order', 'is_shipping_country')


class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = ('subscribe',)


class WholeSaleSerializer(serializers.ModelSerializer):
    license = serializers.IntegerField(required=False)

    class Meta:
        model = WholeSale
        fields = ('license',)


class PostCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True)
    email = serializers.EmailField()
    newsletter = NewsletterSerializer(write_only=True)
    wholesale = WholeSaleSerializer(write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password', 'email','newsletter','wholesale')
        read_only_fields = ('is_staff', 'is_superuser', 'is_active', 'date_joined',)

        def restore_object(self, attrs, instance=None):
            user = super(PostCreateSerializer, self).restore_object(attrs, instance)
            # user.set_password()
            return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=field_length(User.USERNAME_FIELD), required=True)
    password = serializers.CharField(
        max_length=field_length('password'), required=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'], password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('invalid login')
        elif not user.is_active:
            raise serializers.ValidationError(
                'Can not log in as inactive user')
        elif user.is_staff and overridable(
                'OSCARAPI_BLOCK_ADMIN_API_ACCESS', True):
            raise serializers.ValidationError(
                'Staff users can not log in via the rest api')

        # set instance to the user so we can use this in the view
        self.instance = user
        return attrs


class UserAddressSerializer(serializers.ModelSerializer):
    user = PostCreateSerializer(write_only=True)

    class Meta:
        model = UserAddress
        fields = ('line1', 'company', 'line2', 'line3',
                  'line4', 'state', 'postcode', 'phone_number',
                  'fax', 'country', 'newsletter', 'user',)

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['password'] = make_password(user_data['password'], None, get_hasher('pbkdf2_sha256'))
        user_obj = User.objects.create(**user_data)
        user_address = UserAddress.objects.create(user=user_obj, **validated_data)
        user_address.save()
        from_email = settings.EMAIL_HOST_USER
        msg_html = render_to_string('registration.html', {'user': user_data['email']})
        send_mail('subject', msg_html, from_email, [user_data['email']], fail_silently=False)

        return user_address


class CustomerSerializer(serializers.ModelSerializer):
    user = PostCreateSerializer(write_only=True)

    class Meta:
        model = UserAddress
        fields = ('line1', 'state', 'postcode', 'phone_number',
                  'fax', 'country', 'user',)
