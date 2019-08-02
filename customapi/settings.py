import os

from oscar import get_core_apps
from oscar import OSCAR_MAIN_TEMPLATE_DIR
from dbconf import LOCAL_DATABASE ,PRODUCTION_DATABASE
from .parameters import *
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$myj1#btoao6eu8!&oegun(a!$m+#48dr)h*x&&z3)$k6)7ts9'

# SECURITY WARNING: don't run with debug turned on in production!
DEVELOP_MODE = False
DEBUG = TEMPLATE_DEBUG =True
DEBUG = True
ALLOWED_HOSTS = [u'admin.sbs.com',u'localhost',u'127.0.0.1',u'sbsapi.denmasoft.com']

# DJANGO AUTH MODEL DEFINITION
AUTH_USER_MODEL = "auth.User"


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.flatpages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'customapi',
    'corsheaders',
    'widget_tweaks',
    #'oscarapi',
] + get_core_apps(['customapi.address', 'customapi.wishlists', 'customapi.basket', 'customapi.shipping','customapi.dashboard','customapi.dashboard.orders','customapi.dashboard.users'])


CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = ['denmasoft.com', 'sbs.denmasoft.com','sbsapi.denmasoft.com']

CORS_REPLACE_HTTPS_REFERER = True

CSRF_COOKIE_DOMAIN = 'denmasoft.com'

CORS_ORIGIN_WHITELIST = (
    '127.0.0.1:8000',
    '50.63.165.19',
    'denmasoft.com',
    'http://denmasoft.com'
)
CORS_ORIGIN_REGEX_WHITELIST = (
    '127.0.0.1:8000',
    '50.63.165.19',
    'denmasoft.com',
    'http://denmasoft.com'
)

MIDDLEWARE_CLASSES = [
	'customapi.middleware.SbsCorsMiddleware',
	'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',    
    'oscar.apps.basket.middleware.BasketMiddleware',
    #'oscarapi.middleware.ApiGatewayMiddleWare',
]

ROOT_URLCONF = 'customapi.urls'
OSCAR_MAIN_TEMPLATE_DIR = os.path.join(BASE_DIR, 'customapi/templates/oscar')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [OSCAR_MAIN_TEMPLATE_DIR, os.path.join(BASE_DIR, 'customapi/cart/templates'), os.path.join(BASE_DIR, 'customapi/user/templates')],
        #'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'oscar.apps.search.context_processors.search_form',
                'oscar.apps.promotions.context_processors.promotions',
                'oscar.apps.checkout.context_processors.checkout',
                'oscar.apps.customer.notifications.context_processors.notifications',  # noqa
                'oscar.core.context_processors.metadata',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
            ],
        },
    },
]

WSGI_APPLICATION = 'customapi.wsgi.application'



# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True
TIME_ZONE = 'America/New_York'

REST_FRAMEWORK = {
    'CHARSET': 'utf-8',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
   'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
   'PAGE_SIZE': 30
}


#OSCAR GLOBAL settings
from oscar.defaults import *

OSCAR_SHOP_NAME = "South Beauty Supply"
OSCAR_HOMEPAGE = ""
OSCAR_SHOP_TAGLINE = ""


OSCAR_ALLOW_ANON_REVIEWS = True
OSCAR_MODERATE_REVIEWS = True
OSCAR_DEFAULT_CURRENCY = "USD"
OSCAR_IMAGE_FOLDER = "products/%Y/%m/"

#Haystack conections
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': '',
    },
}

# Database conections
DATABASES = PRODUCTION_DATABASE

# Static files (CSS, JavaScript, Images)
SITE_ID = 1
MEDIA_URL = '/public/'
STATIC_URL = os.path.join(BASE_DIR,'static/')
MEDIA_ROOT = os.path.join(BASE_DIR,'public')
TAX = TAX
if DEVELOP_MODE == False:
    STATIC_URL = '/static/'
    DATABASES = PRODUCTION_DATABASE
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = False
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = 'denmaserver@denmasoft.com'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 25
DEFAULT_FROM_EMAIL = 'denmaserver@denmasoft.com'
STRIPE_API_KEY = STRIPE_API_KEY
STRIPE_PUBLISH_KEY = STRIPE_PUBLISH_KEY
PAYPAL_CLIENT_ID = PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET = PAYPAL_CLIENT_SECRET
FRONT_URL = "http://sbs.denmasoft.com/success-purchase"
RECOVER_URL = "http://sbs.denmasoft.com/reset-password/"
API_URL = "http://sbsapi.denmasoft.com/api"
CONTACT_EMAIL = "yalint86@gmail.com"
OSCAR_ALLOW_ANON_CHECKOUT = True
FACEBOOK_APP_ID = FACEBOOK_APP_ID
FACEBOOK_CLIENT_ID = FACEBOOK_CLIENT_ID
FACEBOOK_REDIRECT = FACEBOOK_REDIRECT
GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID
GOOGLE_SECRET_CLIENT = GOOGLE_SECRET_CLIENT
GOOGLE_REDIRECT = GOOGLE_REDIRECT
CREDIT_KEY = CREDIT_KEY
MAILCHIMP_KEY = MAILCHIMP_KEY
MAILCHIMP_USER = MAILCHIMP_USER
SHIPPO_KEY = SHIPPO_KEY
FREE_SHIPPING_OVER = 99.00
ZIP_CODE = 33135
