from django.contrib.auth.models import User
import binascii,os
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from django.contrib.auth.hashers import *
from django.core.exceptions import (PermissionDenied, ObjectDoesNotExist)
from rest_framework.generics import (CreateAPIView, ListAPIView, RetrieveUpdateAPIView)
from rest_framework.authentication import (TokenAuthentication, SessionAuthentication)
from rest_framework.renderers import JSONRenderer
from django.shortcuts import redirect
from django.conf import settings
from customapi.address.models import UserAddress
from customapi.user.models import Newsletter
from customapi.user.models import WholeSale
from customapi.user.models import SocialProfile
from customapi.user.models import CreditCard
from customapi.license.models import License
from oscar.apps.address.models import Country
from .serializers import (CountrySerializer, UserAddressSerializer, LoginSerializer, CustomerSerializer)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from oscar.core.loading import get_model
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from rest_framework.authtoken.models import Token
from braces.views import CsrfExemptMixin
from oscarapi.utils import login_and_upgrade_session
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.core.mail import send_mail
from customapi.user import operations
from customapi.cart import operations as cart_ops
import facebook
import httplib2
from googleapiclient.discovery import build
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.shortcuts import render
from oauth2client.contrib import xsrfutil
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import OAuth2WebServerFlow
from urlparse import parse_qs, urlparse
from urllib import urlencode
from Crypto.Cipher import AES
import base64
from mailchimp3 import MailChimp


__all__ = ('CustomerLogoutView',)

Basket = get_model('basket', 'Basket')
Order = get_model('order', 'Order')
FLOW = OAuth2WebServerFlow(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_SECRET_CLIENT,
                           ('https://www.googleapis.com/auth/plus.me','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile'),
            redirect_uri='http://admin.sbs.websingit.com/api/google/callback/')


class PostCreateAPIView(CreateAPIView):
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer


class PostRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserAddressSerializer


class CountryList(ListAPIView):

    serializer_class = CountrySerializer

    def get(self, request, pk=None, format=None):
        countries = []
        _countries = Country.objects.all()
        for country in _countries:
            ser = CountrySerializer(country, context={'request': request})
            countries.append(ser.data)
        return Response({'result': countries})


class CustomerLoginView(APIView):
    authentication_classes = (TokenAuthentication,)
    """
    Api for logging in customers.    

    POST(username, password):
    1. The user will be authenticated. The next steps will only be
       performed is login is succesful. Logging in logged in users results in
       405.
    2. The anonymous cart will be merged with the private cart associated with
       that authenticated user.
    3. A new session will be started, this session identifies the authenticated
       user for the duration of the session, without further need for
       authentication.
    4. The new, merged cart will be associated with this session.
    5. The anonymous session will be terminated.
    6. A response will be issued containing the new session id as a header
       (only when the request contained the session header as well).

    """
    serializer_class = LoginSerializer

    def post(self, request, format=None):
        ser = self.serializer_class(data=request.data)
        if ser.is_valid():
            validated_data = ser.validated_data
            username = validated_data['username']
            _password = validated_data['password']
            user = User
            try:
                user = User.objects.get(username=username)
                if user.check_password(_password):
                    response = operations.customer_data(user, request)
                    return Response(response)
            except user.DoesNotExist:
                return Response(
                    {'message': 'Something went wrong with your credentials.'},
                    status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {'message': 'Please, check username and password.'},
            status=status.HTTP_401_UNAUTHORIZED)


class CustomerLogoutView(CsrfExemptMixin, APIView):
    authentication_classes = []

    def post(self, request, format=None):
        operations.customer_logout(request)
        return Response("")


class CustomerProfileView(APIView):
    authentication_classes = (TokenAuthentication,)
    """
        Api for updating customers data.  
        if the customer password needs to be changed, the new password needs to be on the values array otherwise do not\
        send it..
        POST:
            "username": "",
            "first_name": "",
            "last_name": "",
            "email":""
            "password":""
            "line1": "",
            "line2": "",
            "line3": "",
            "line4": "city",
            "state": "",
            "phone_number": "",
            "postcode": "",
            "fax": "",
            "country": "",
            "subscribe_newsletter": ""

        """

    def update_user_data(self, user, request):

        count = 0
        if 'username' in request.data:
            user.username = request.data['username']
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
            user.username = request.data['email']
        if 'password' in request.data:
            if request.data['password']:
                user.password = make_password(request.data['password'], None, get_hasher('pbkdf2_sha256'))
        try:
            user.save()
        except IntegrityError as e:
            return Response({'message': 'Username or email is already in use.'}, status=status.HTTP_409_CONFLICT)
        if 'license' in request.data:
            license = request.data['license']
            if license:
                check = operations.validate_license(license, user)
                if check == 'Not Valid':
                    return Response({'message': 'That license is not valid.'}, status=status.HTTP_409_CONFLICT)
                if check == 'In Use':
                    return Response({'message': 'License "%s" is already in use.' % license},
                                    status=status.HTTP_409_CONFLICT)
                try:
                    wholesale = WholeSale.objects.get(user=user)
                    if wholesale:
                        wholesale.license = license
                        wholesale.save()
                except ObjectDoesNotExist:
                    wholesale = WholeSale.objects.create(user=user, license=license)
                    wholesale.save()
            else:
                try:
                    wholesale = WholeSale.objects.get(user=user)
                    if wholesale:
                        wholesale.delete()
                except ObjectDoesNotExist:
                    pass
        while 'address_'+str(count) in request.data:
            line1 = request.data['address_' + str(count)]
            if line1:
                country = request.data['country_'+str(count)]
                country = get_object_or_404(Country, iso_3166_1_a2=country)
                address_id = request.data['address_id_'+str(count)]
                state = request.data['state_' + str(count)]
                line4 = request.data['city_' + str(count)]
                postcode = request.data['postcode_' + str(count)]
                if address_id:
                    try:
                        addr, updated = UserAddress.objects.update_or_create(
                            pk=address_id,
                            defaults={
                                'user': user,
                                'country': country,
                                'line1': line1,
                                'line4': line4,
                                'state': state,
                                'postcode': postcode,
                            }
                        )
                    except IntegrityError as e:
                        return Response({'message': 'One or more addresses are already in use.'},status=status.HTTP_409_CONFLICT)
                else:
                    try:
                        addr = UserAddress.objects.create(
                                user=user, country=country, line1=line1, line4=line4, state=state, postcode=postcode)
                    except IntegrityError as e:
                        return Response({'message': 'One or more addresses are already in use.'},
                                        status=status.HTTP_409_CONFLICT)
            count = count+1
        if 'subscribe' in request.data:
            if request.data['subscribe']:
                newsletter = Newsletter
                try:
                    newsletter = Newsletter.objects.get(user=user)
                    newsletter.subscribe = request.data['subscribe']
                    newsletter.save()
                    operations.process_user_mailchimp(user, request.data['subscribe'])
                except newsletter.DoesNotExist:
                    newsletter = Newsletter.objects.create(user=user,subscribe=request.data['subscribe'])
                    newsletter.save()
                    operations.process_user_mailchimp(user, request.data['subscribe'])

        if 'creditCard' in request.data:
            iv = os.urandom(16)
            credit_card = operations.encryptCard(request.data['creditCard'])
            cch = CreditCard.objects.filter(card=credit_card).count()
            if cch is 0:
                card = CreditCard.objects.create(user=user.id, card=credit_card, holder=request.data['first_name'] + ' ' + request.data['last_name'],
                                                 salt=iv)
                card.save()
            else:
                return Response({'message': 'That credit card is in use.'}, status=status.HTTP_409_CONFLICT)
        response = operations.customer_data(user, request)
        from_email = settings.DEFAULT_FROM_EMAIL
        contact_email = settings.CONTACT_EMAIL
        notifyadmin = render_to_string('notifyuser.html', {
            'message': 'User '+user.first_name+' '+user.last_name+' has changed his/her personal information',
            'firstName': user.first_name,
            'lastName': user.last_name,
            'UserName': user.username,
            'license': license,
            'email': response['email']})
        notifyuser = render_to_string('notifyuser.html', {
            'message': ' You have changed your personal information',
            'firstName': user.first_name,
            'lastName': user.last_name,
            'UserName': user.username,
            'license': license,
            'email': response['email']})
        send_mail('subject', notifyadmin, from_email, [contact_email], fail_silently=False,
                  html_message=notifyadmin)
        send_mail('subject', notifyuser, from_email, [response['email']], fail_silently=False,
                  html_message=notifyuser)
        return Response(response)

    def get(self, request, pk=None, format='json'):
        user = User.objects.get(id=pk)
        response = operations.customer_data(user, request)
        return Response(response)

    def post(self, request, format=None):
        user = get_object_or_404(User, pk=request.data['user_id'])
        token = request.data['token']
        tokken = Token
        token_user = None
        try:
            tokken = Token.objects.get(key=token)
            token_user = tokken.user
        except tokken.DoesNotExist:
            return Response({'message': 'You are not who you say you are. Sorry.'}, status=status.HTTP_409_CONFLICT)
        if user.id == token_user.id:
            return self.update_user_data(user, request)
        return Response({'message': 'You are not who you say you are. Sorry.'}, status=status.HTTP_409_CONFLICT)


class CustomerRegisterView(APIView):
    authentication_classes = (TokenAuthentication,)
    """
        """
    #serializer_class = CustomerSerializer

    def validate_license(self, license):
        licensemodel = License.objects.filter(license_number=license).count()
        if licensemodel is 0:
            licensemodel = License.objects.filter(alternate_license_number=license).count()
        if licensemodel is 0:
            return True
        return False

    def validate_usage(self, license):
        usage = WholeSale.objects.filter(license=license).count()
        if usage is 0:
            return False
        return True

    def post(self, request, format=None):

        user = User
        wholesale = WholeSale
        params = request.data
        subscribe = False
        line1 = None
        line4 = None
        state = None
        postcode = None
        fax = None
        country = None
        if 'username' not in params:
            return Response({'message': 'You must provide a username.'}, status=status.HTTP_409_CONFLICT)
        if 'password' not in params:
            return Response({'message': 'You must provide a password.'}, status=status.HTTP_409_CONFLICT)
        if 'email' not in params:
            return Response({'message': 'You must provide an email.'}, status=status.HTTP_409_CONFLICT)
        #if 'phone_number' not in params:
        #    return Response({'message': 'You must provide a phone number.'}, status=status.HTTP_409_CONFLICT)
        if 'first_name' not in params:
            return Response({'message': 'Please, tell us your name.'}, status=status.HTTP_409_CONFLICT)
        if 'last_name' not in params:
            return Response({'message': 'You must provide your last name.'}, status=status.HTTP_409_CONFLICT)
        username = params['username']
        _password = params['password']
        password = make_password(_password, None, get_hasher('pbkdf2_sha256'))
        #phone_number = params['phone_number']
        email = params['email']
        first_name = params['first_name']
        last_name = params['last_name']
        if 'subscribe' in params:
            subscribe = params['subscribe']
        if 'address' in params:
            line1 = params['address']
        if 'city' in params:
            line4 = params['city']
        if 'state' in params:
            state = params['state']
        if 'postcode' in params:
            postcode = params['postcode']
        #if 'fax' in params:
        #    fax = params['fax']
        if 'country' in params:
            country = params['country']
            country = Country.objects.get(iso_3166_1_a2=country)
        license = None
        if 'license' in params:
            license = params['license']
            if license:
                check = operations.validate_license(license)
                if check == 'Not Valid':
                    return Response({'message': 'That license is not valid.'}, status=status.HTTP_409_CONFLICT)
                if check == 'In Use':
                    return Response({'message': 'License "%s" is already in use.' % license}, status=status.HTTP_409_CONFLICT)
        try:
            user = User.objects.get(username=username)
        except user.DoesNotExist:
            try:
                user = User.objects.get(email=email)
            except user.DoesNotExist:
                user = User.objects.create(username=username,
                                               password=password,
                                               email=email,
                                               first_name=first_name,
                                               last_name=last_name)
                user.save()
                if 'creditCard' in params:
                    key = settings.CREDIT_KEY
                    iv = os.urandom(16)
                    mode = AES.MODE_CBC
                    encryptor = AES.new(key, mode, iv)
                    credit_card = operations.encryptCard(params['creditCard'])
                    cch = CreditCard.objects.filter(card=credit_card).count()
                    if cch is 0:
                        card = CreditCard.objects.create(user=user.id, card=credit_card, holder=first_name+' '+last_name, salt=iv)
                        card.save()
                    else:
                        return Response({'message': 'That credit card is in use.'}, status=status.HTTP_409_CONFLICT)
                newsletter = Newsletter.objects.create(user=user, subscribe=subscribe)
                newsletter.save()
                operations.process_user_mailchimp(user, subscribe)
                if license:
                    wholesale = WholeSale.objects.create(user=user, license=license)
                    wholesale.save()
                if line1 is not None and state is not None and postcode is not None and country is not None:
                    user_address = UserAddress.objects.create(user=user,
                                                              line1=line1,
                                                              line4=line4,
                                                              state=state,
                                                              postcode=postcode,
                                                              country=country)
                    user_address.save()
                # operations.customer_login(request, user)
                response = operations.customer_data(user, request)
                from_email = settings.DEFAULT_FROM_EMAIL
                msg_html = render_to_string('register.html', {
                    'message': 'Below you will find your personal information',
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'UserName': user.username,
                    'password': _password,
                    'email': response['email']})
                send_mail('User Registration', msg_html, from_email, [response['email']], fail_silently=False, html_message=msg_html)
                notifyuser = render_to_string('notifyuser.html', {
                    'message': 'A new user has registered on the system. Below you will find his/her personal information.',
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'UserName': user.username,
                    'license': license,
                    'email': response['email']})
                contact_email = settings.CONTACT_EMAIL
                send_mail('user registration', notifyuser, from_email, [contact_email], fail_silently=False,
                          html_message=notifyuser)
                return Response(response)
            return Response(
                {'message': 'Email "%s" is already in use.' % email},
                status=status.HTTP_409_CONFLICT)
        return Response(
            {'message': 'Username "%s" is already in use.' % username},
            status=status.HTTP_409_CONFLICT)


class SendContactView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        name = request.data['name']
        if 'email' not in request.data:
            return Response(
                {'message': 'email address not provided'},
                status=status.HTTP_409_CONFLICT)
        email = request.data['email']
        message = request.data['message']
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(name, message, from_email, [email, from_email, settings.CONTACT_EMAIL], fail_silently=False)
        return Response(
            {'message': 'message sent'},
            status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        token = request.data['token']
        password = request.data['password']
        decode = binascii.unhexlify(token).decode()
        try:
            tokken = Token.objects.get(key=decode)
            m_user = User.objects.get(pk=tokken.user.id)
            m_user.set_password(password) #= make_password(password, None, get_hasher('pbkdf2_sha256'))
            m_user.save()
            key = binascii.hexlify(os.urandom(20)).decode()
            Token.objects.filter(user=tokken.user).update(key=key)
            return Response({'message': 'Your password has been changed successfully'}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'message': 'You are doing something wrong.'}, status=status.HTTP_409_CONFLICT)
        #m_user = User.objects.get(email=email)
        #temppass = User.objects.make_random_password(length=8,allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')
        #password = m_user.username + "_" + temppass
        #m_user.password = make_password(password, None, get_hasher('pbkdf2_sha256'))
        #m_user.save()


class RecoverPasswordView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        if 'email' not in request.data:
            return Response(
                {'message': 'email address not provided'},
                status=status.HTTP_409_CONFLICT)
        email = request.data['email']
        try:
            m_user = User.objects.get(email=email)
            tokken = Token.objects.get(user=m_user)
            encode = binascii.hexlify(tokken.key).decode()
            from_email = settings.DEFAULT_FROM_EMAIL
            changepassuser = render_to_string('changepasswd.html', {
                'firstName': m_user.first_name,
                'lastName': m_user.last_name,
                'url': settings.RECOVER_URL+str(encode)
                })
            send_mail('Password recovery', changepassuser, from_email, [email], fail_silently=False,
                      html_message=changepassuser)
            return Response({'message': 'An email have been sent to '+str(m_user.email)}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({'message': 'That email does not exist on the system.'}, status=status.HTTP_409_CONFLICT)
        #m_user = User.objects.get(email=email)
        #temppass = User.objects.make_random_password(length=8,allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')
        #password = m_user.username + "_" + temppass
        #m_user.password = make_password(password, None, get_hasher('pbkdf2_sha256'))
        #m_user.save()



class FacebookLoginView(APIView):
    def get(self,request,format=None):
        actual_url = facebook.auth_url(settings.FACEBOOK_APP_ID, settings.FACEBOOK_REDIRECT)
        return redirect(actual_url+'&scope=email')


class FacebookCallbackView(APIView):
    def get(self, request, format=None):
        code = request.GET.get('code', '')
        token = facebook.GraphAPI().get_access_token_from_code(code, settings.FACEBOOK_REDIRECT, settings.FACEBOOK_APP_ID, settings.FACEBOOK_CLIENT_ID)
        graph = facebook.GraphAPI(access_token=token['access_token'])
        result = graph.request('/me?fields=id,name,email,first_name,last_name')
        profile = SocialProfile
        try:
            profile = SocialProfile.objects.get(userid=result['id'])
            response = operations.customer_data(profile.user, request)
        except profile.DoesNotExist:
            username = result['name'].replace(' ', '.')
            password = make_password(result['id'], None, get_hasher('pbkdf2_sha256'))
            user = User.objects.create(username=username,
                                       password=password,
                                       email=result['email'],
                                       first_name=result['first_name'],
                                       last_name=result['last_name'])
            user.save()
            newsletter = Newsletter.objects.create(user=user, subscribe=False)
            newsletter.save()
            profile = SocialProfile.objects.create(user=user,
                                             full_name=result['name'],
                                             username=username,
                                             userid=result['id'], network='FACEBOOK')
            profile.save()
            response = operations.customer_data(profile.user, request)

        return Response(response)


class GoogleLoginView(APIView):
    def get(self,request,format=None):
        authorize_url = FLOW.step1_get_authorize_url()
        return HttpResponseRedirect(authorize_url)


class GoogleCallbackView(APIView):
    def get(self, request, format=None):
        credential = FLOW.step2_exchange(request.GET)
        http = httplib2.Http()
        http = credential.authorize(http)
        service = build("plus", "v1", http=http)
        result = service.people().get(userId='me').execute()
        profile = SocialProfile
        try:
            profile = SocialProfile.objects.get(userid=result['id'])
            response = operations.customer_data(profile.user, request)
        except profile.DoesNotExist:
            username = result['displayName'].replace(' ', '.')
            password = make_password(result['id'], None, get_hasher('pbkdf2_sha256'))
            user = User.objects.create(username=username,
                                       password=password,
                                       email=result['emails'][0]['value'],
                                       first_name=result['name']['givenName'],
                                       last_name=result['name']['familyName'])
            user.save()
            newsletter = Newsletter.objects.create(user=user, subscribe=False)
            newsletter.save()
            profile = SocialProfile.objects.create(user=user,
                                                   full_name=result['displayName'],
                                                   username=username,
                                                   userid=result['id'], network='GOOGLE')
            profile.save()
            response = operations.customer_data(profile.user, request)

        return Response(response)


class EncryptCardView(APIView):
    def get(self, request, format=None):
        card = request.GET.get('card', '')
        encrypted = operations.encryptCard(card)
        return Response({'card': encrypted})


class DecryptCardView(APIView):
    def get(self, request, format=None):
        card = request.GET.get('card', '')
        encrypted = operations.decryptCard(card)
        return Response({'card': encrypted})


class SubscribeUserView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, format=None):
        email = request.data['email']
        first_name = request.data['first_name']
        last_name = request.data['last_name']
        client = MailChimp(settings.MAILCHIMP_USER, settings.MAILCHIMP_KEY)
        obj = client.lists.all(get_all=True, fields="lists.name,lists.id")
        lists = obj['lists']
        for mlist in lists:
            client.lists.members.create(mlist['id'], {
                'email_address': email,
                'status': 'subscribed',
                'merge_fields': {
                    'FNAME': first_name,
                    'LNAME': last_name,
                },
            })
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail('South Beauty Supply Newsletter Subscription', 'You have subscribed to South Beauty Supply Newsletter', from_email, [email], fail_silently=False)
        send_mail('South Beauty Supply Newsletter Subscription', str(first_name) +' '+str(last_name)+ ' has subscribed to South Beauty Supply Newsletter', from_email, [settings.CONTACT_EMAIL], fail_silently=False)
        return Response({'message': 'message sent'},status=status.HTTP_200_OK)


class FakeEmailView(APIView):
    def get(self, request, format=None):
        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail('User Registration', 'sadasdad', from_email, ['yalint86@gmail.com'], fail_silently=False)
        except e:
                raise ValueError(e)
        return Response({'re':'re'})


class RemoveUserAddress(APIView):
    authentication_classes = (TokenAuthentication,)
    def post(self, request, format=None):
        #user = get_object_or_404(User, pk=request.data['user'])
        address = UserAddress
        try:
            address = get_object_or_404(UserAddress, pk=request.data['address'])
            address.delete()
            return Response({'message': 'Address removed successfully.'}, status=status.HTTP_200_OK)
        except address.DoesNotExist:
            return Response({'message': 'That address does not exist.'}, status=status.HTTP_404_NOT_FOUND)


class UserPurchaseHistory(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, pk=None, format=None):
        result = []
        orders = Order.objects.filter(user=pk)
        for order in orders:
            tax = float(settings.TAX) * 100
            tax_value = float(order.total_incl_tax) * float(settings.TAX)
            result.append({'number': order.number, 'date': order.date_placed, 'total': order.total_incl_tax,
                        'items': cart_ops.getitems(order),
                        'discounts': cart_ops.getdiscounts(order),
                        'shippings': cart_ops.getShipping(order),
                        'shipping_address': cart_ops.getShippingAddress(order.shipping_address),
                        'tax_name': str(tax) + "% tax",
                        'tax_value': tax_value})
        return Response(result)