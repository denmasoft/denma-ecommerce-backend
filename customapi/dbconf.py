import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



# Local database configuration
LOCAL_DATABASE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'sbs-db.sqlite3')
    }
}

#Production database configuration
PRODUCTION_DATABASE = {
    'default': {
        'ENGINE':'django.db.backends.mysql',
        'NAME': 'sbsdb',
        'USER': 'denma',
        'PASSWORD':'!1123Py85!',
        'HOST':'localhost',
        'PORT':'3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}



