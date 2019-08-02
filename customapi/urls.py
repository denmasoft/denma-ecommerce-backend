from django.conf.urls import include, url
from django.contrib import admin
from django.http import HttpResponseRedirect

from customapi.app import application as api
from oscar.app import application as oscar

from django.conf.urls.static import static


import settings

urlpatterns = [

    url(r'^$',lambda x: HttpResponseRedirect('/dashboard')),
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include(api.urls)),
    url(r'', include(oscar.urls))
]

# Debug settings for static images
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
